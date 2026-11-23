from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# A typical night resting on fewer past nights than this is noise, not a pattern.
MIN_HISTORY = 3

# The last night of history: the latest quarter isn't complete yet (ADR 0002).
HISTORY_END = """
SELECT (date_trunc('quarter', max(last_night)) - interval '1 day')::date AS last FROM campground
"""
# A campground is active if it was booked in the year before the history ends. A campground
# open every season is; one renamed "... - OBSELETE" and retired, or closed for good, isn't.
ACTIVE_DAYS = 365

# ADR 0002: the nights asked for → their kind of night → each campground's typical night.
# A campground must have a typical for every night asked for, with enough history: a missing
# kind means it's usually closed then (Cape York in the wet), not quiet.
# Equally quiet campgrounds go bigger first: peak is the campground's busy night (95th
# percentile, in sites), so a real campground at 0% comes before a bush camp whose busy night
# is one site.
# Pages are keyset: (busyness, -peak, id) is unique and ordered, so "after this one" never
# skips or repeats a row. busyness is rounded because a float average can differ in its last
# bits between runs, and the cursor compares it exactly.
SEARCH = text(f"""
WITH asked AS (
    SELECT kind FROM calendar_day WHERE night >= :arrive AND night < :depart
),
ranked AS (
    SELECT c.id, c.name, c.park_name,
           CAST(round(CAST(avg(t.busyness) AS numeric), 6) AS float8) AS busyness,
           avg(t.sites) AS typical_sites, min(t.nights) AS history, max(t.peak) AS peak,
           c.lat, c.lon, c.location_source, c.location_flags, c.osm_type, c.osm_id
    FROM asked a
    JOIN campground_typical t ON t.kind = a.kind
    JOIN campground c ON c.id = t.campground_id
    WHERE c.last_night > ({HISTORY_END}) - CAST(:active_days AS integer)
      AND (CAST(:park AS text) IS NULL OR c.park_name = :park)
      AND (CAST(:pattern AS text) IS NULL OR c.name ILIKE :pattern OR c.park_name ILIKE :pattern)
    GROUP BY c.id
    HAVING count(*) = (SELECT count(*) FROM asked) AND min(t.nights) >= :min_history
)
SELECT * FROM ranked
WHERE CAST(:after_id AS integer) IS NULL
   OR (busyness, -peak, id)
      > (CAST(:after_busyness AS float8), -CAST(:after_peak AS float8), :after_id)
ORDER BY busyness, peak DESC, id
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
    peak: float  # its busy night: the 95th percentile of its open nights, in sites
    lat: float | None
    lon: float | None
    location_source: str | None
    location_flags: list[str]
    osm_type: str | None  # node, way or relation
    osm_id: int | None


@dataclass(frozen=True)
class After:
    """Where the previous page ended: the last campground's busyness, peak and id."""

    busyness: float
    peak: float
    id: int


def contains(q: str) -> str:
    """An ILIKE pattern for q anywhere, with q's own %, _ and \\ as plain characters."""
    # Backslash is Postgres's default LIKE escape; escape it first, or it would double the rest.
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


async def search_quiet(
    session: AsyncSession,
    arrive: date,
    depart: date,
    park: str | None,
    q: str | None,
    limit: int | None,
    after: After | None = None,
) -> list[QuietCampground]:
    """Campgrounds that are usually quietest on the nights from arrive to depart (exclusive).

    `q` narrows to names or park names containing it, ignoring case. `after` starts the page
    after that campground. `limit=None` returns every result (Postgres reads LIMIT NULL as none).
    """
    result = await session.execute(
        SEARCH,
        {
            "arrive": arrive,
            "depart": depart,
            "park": park,
            "pattern": None if q is None else contains(q),
            "limit": limit,
            "after_busyness": None if after is None else after.busyness,
            "after_peak": None if after is None else after.peak,
            "after_id": None if after is None else after.id,
            "active_days": ACTIVE_DAYS,
            "min_history": MIN_HISTORY,
        },
    )
    return [QuietCampground(**row) for row in result.mappings()]
