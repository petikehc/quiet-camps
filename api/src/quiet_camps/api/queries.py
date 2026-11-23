from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from quiet_camps.ingest.geo import EARTH_RADIUS_KM

# A typical night resting on fewer past nights than this is noise, not a pattern.
MIN_HISTORY = 3

# The last night of history: the latest quarter isn't complete yet (ADR 0002).
HISTORY_END = """
SELECT (date_trunc('quarter', max(last_night)) - interval '1 day')::date AS last FROM campground
"""
# A campground is active if it was booked in the year before the history ends. A campground
# open every season is; one renamed "... - OBSELETE" and retired, or closed for good, isn't.
ACTIVE_DAYS = 365
ACTIVE = f"c.last_night > ({HISTORY_END}) - CAST(:active_days AS integer)"  # campground c
# Straight-line km from (:near_lat, :near_lon) to campground c: geo.km (haversine) in SQL.
# No PostGIS (ADR 0003): a few hundred campgrounds are quick to measure one by one.
DISTANCE = f"""(2 * {EARTH_RADIUS_KM} * asin(sqrt(
    sin(radians(c.lat - CAST(:near_lat AS float8)) / 2) ^ 2
    + cos(radians(CAST(:near_lat AS float8))) * cos(radians(c.lat))
      * sin(radians(c.lon - CAST(:near_lon AS float8)) / 2) ^ 2)))"""

# The campgrounds a search is about: active, and in the park, matching q, and near the place
# when those are asked for. The search and the year view both pick by it.
CHOSEN = f"""{ACTIVE}
      AND (CAST(:park AS text) IS NULL OR c.park_name = :park)
      AND (CAST(:pattern AS text) IS NULL OR c.name ILIKE :pattern OR c.park_name ILIKE :pattern)
      AND (CAST(:near_lat AS float8) IS NULL
           OR (c.lat IS NOT NULL AND {DISTANCE} <= CAST(:within_km AS float8)))"""

# Each campground's typical for each night of `nights` (rows with night, kind, fallback_kind):
# its own kind of night when enough past nights back it, else the broader fallback kind when
# enough years do (day_kinds.py: the weekday across the fortnight, a holiday's nights
# together; a pool has more nights a year, so it's judged by years). Neither: no row, usually
# closed then.
USUAL = """
    SELECT DISTINCT ON (t.campground_id, d.night)
           t.campground_id, d.night, t.busyness, t.sites, t.nights, t.peak
    FROM {nights} d
    JOIN campground_typical t ON t.kind IN (d.kind, d.fallback_kind)
    WHERE ((t.kind = d.kind AND t.nights >= :min_history)
           OR (t.kind = d.fallback_kind AND t.years >= :min_history)){also}
    ORDER BY t.campground_id, d.night, t.kind = d.kind DESC"""

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
    SELECT night, kind, fallback_kind
    FROM calendar_day WHERE night >= :arrive AND night < :depart
),
usual AS ({USUAL.format(nights="asked", also="")}
),
ranked AS (
    SELECT c.id, c.name, c.park_name,
           CAST(round(CAST(avg(u.busyness) AS numeric), 6) AS float8) AS busyness,
           avg(u.sites) AS typical_sites, min(u.nights) AS history, max(u.peak) AS peak,
           c.lat, c.lon, c.location_source, c.location_flags, c.osm_type, c.osm_id,
           CASE WHEN CAST(:near_lat AS float8) IS NULL THEN NULL ELSE {DISTANCE} END
               AS distance_km
    FROM usual u
    JOIN campground c ON c.id = u.campground_id
    WHERE {CHOSEN}
    GROUP BY c.id
    HAVING count(*) = (SELECT count(*) FROM asked)
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
    distance_km: float | None  # from the place searched near; None without one


@dataclass(frozen=True)
class Near:
    """Within km of a place: where someone starts from, or wants to be near."""

    lat: float
    lon: float
    km: float


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
    near: Near | None = None,
) -> list[QuietCampground]:
    """Campgrounds that are usually quietest on the nights from arrive to depart (exclusive).

    `q` narrows to names or park names containing it, ignoring case. `near` narrows to located
    campgrounds within its km, and gives each one's distance. `after` starts the page after
    that campground. `limit=None` returns every result (Postgres reads LIMIT NULL as none).
    """
    result = await session.execute(
        SEARCH,
        {
            **chosen(park, q, near),
            "arrive": arrive,
            "depart": depart,
            "limit": limit,
            "after_busyness": None if after is None else after.busyness,
            "after_peak": None if after is None else after.peak,
            "after_id": None if after is None else after.id,
            "min_history": MIN_HISTORY,
        },
    )
    return [QuietCampground(**row) for row in result.mappings()]


def chosen(park: str | None, q: str | None, near: Near | None) -> dict[str, object]:
    """CHOSEN's parameters."""
    return {
        "active_days": ACTIVE_DAYS,
        "park": park,
        "pattern": None if q is None else contains(q),
        "near_lat": None if near is None else near.lat,
        "near_lon": None if near is None else near.lon,
        "within_km": None if near is None else near.km,
    }


# Each night of a year, how busy the chosen campgrounds usually are together: the mean of
# their typical busyness for that kind of night, over those open then (with enough history).
# None when none are: a night they're all usually closed.
AREA_YEAR = text(f"""
WITH picked AS (
    SELECT c.id FROM campground c WHERE {CHOSEN}
),
nights AS (
    SELECT night, kind, fallback_kind FROM calendar_day WHERE night BETWEEN :first AND :last
),
usual AS ({USUAL.format(nights="nights", also=" AND t.campground_id IN (SELECT id FROM picked)")}
)
SELECT d.night, avg(u.busyness) AS busyness, count(u.campground_id)::int AS open
FROM nights d
LEFT JOIN usual u ON u.night = d.night
GROUP BY d.night
ORDER BY d.night
""")


@dataclass(frozen=True)
class AreaNight:
    night: date
    busyness: float | None  # the mean over the campgrounds open; None when none are
    open: int  # how many of the chosen campgrounds are usually open that night


async def area_year(
    session: AsyncSession,
    first: date,
    last: date,
    park: str | None,
    q: str | None,
    near: Near | None,
) -> list[AreaNight]:
    """How busy the chosen campgrounds usually are on each night from first to last."""
    result = await session.execute(
        AREA_YEAR,
        {**chosen(park, q, near), "first": first, "last": last, "min_history": MIN_HISTORY},
    )
    return [AreaNight(**row) for row in result.mappings()]
