from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from quiet_camps.db.locations import ACTIVE_SINCE

# A typical night resting on fewer past nights than this is noise, not a pattern.
MIN_HISTORY = 3

# ADR 0002: the nights asked for → their kind of night → each campground's typical night.
# A campground must have a typical for every night asked for, with enough history: a missing
# kind means it's usually closed then (Cape York in the wet), not quiet.
SEARCH = text("""
WITH asked AS (
    SELECT kind FROM calendar_day WHERE night >= :arrive AND night < :depart
)
SELECT c.id, c.name, c.park_name, avg(t.busyness) AS busyness, avg(t.sites) AS typical_sites,
       min(t.nights) AS history, c.lat, c.lon, c.location_source, c.location_flags
FROM asked a
JOIN campground_typical t ON t.kind = a.kind
JOIN campground c ON c.id = t.campground_id
WHERE c.last_night >= :active_since
  AND (CAST(:park AS text) IS NULL OR c.park_name = :park)
GROUP BY c.id
HAVING count(*) = (SELECT count(*) FROM asked) AND min(t.nights) >= :min_history
ORDER BY busyness, c.id
LIMIT :limit
""")


@dataclass(frozen=True)
class QuietCampground:
    id: int
    name: str
    park_name: str
    busyness: float  # mean over the nights asked for; 1.0 = as busy as its own busiest nights
    typical_sites: float
    history: int  # past nights behind the thinnest typical night
    lat: float | None
    lon: float | None
    location_source: str | None
    location_flags: list[str]


async def search_quiet(
    session: AsyncSession, arrive: date, depart: date, park: str | None, limit: int
) -> list[QuietCampground]:
    """Campgrounds that are usually quietest on the nights from arrive to depart (exclusive)."""
    result = await session.execute(
        SEARCH,
        {
            "arrive": arrive,
            "depart": depart,
            "park": park,
            "limit": limit,
            "active_since": ACTIVE_SINCE,
            "min_history": MIN_HISTORY,
        },
    )
    return [QuietCampground(**row) for row in result.mappings()]
