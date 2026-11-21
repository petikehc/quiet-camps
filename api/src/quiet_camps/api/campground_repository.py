from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from quiet_camps.api.campground_service import (
    CalendarNight,
    LeadCount,
    MonthSites,
    NightCampers,
    YearCampground,
)
from quiet_camps.api.queries import MIN_HISTORY
from quiet_camps.db.models import Campground

# The last night of history: the latest quarter isn't complete yet (ADR 0002).
HISTORY_END = """
SELECT (date_trunc('quarter', max(last_night)) - interval '1 day')::date AS last FROM campground
"""

# Every night of the year for one campground (none if it doesn't exist): its typical night
# from campground_typical, as the search reads it, and the sites actually booked. Booked
# sites stop where the history does.
CALENDAR = text(f"""
WITH history AS ({HISTORY_END}),
booked AS (
    SELECT n.night, sum(n.sites)::int AS sites
    FROM area_night n
    JOIN camping_area a ON a.id = n.area_id
    WHERE a.campground_id = :campground_id AND n.night >= :first AND n.night < :next
    GROUP BY n.night
)
SELECT d.night, d.kind, d.holiday,
       t.sites AS typical_sites, t.busyness,
       CASE WHEN d.night <= h.last THEN coalesce(b.sites, 0) END AS sites
FROM campground c
JOIN calendar_day d ON d.night >= :first AND d.night < :next
CROSS JOIN history h
LEFT JOIN campground_typical t
    ON t.campground_id = c.id AND t.kind = d.kind AND t.nights >= :min_history
LEFT JOIN booked b ON b.night = d.night
WHERE c.id = :campground_id
ORDER BY d.night
""")


# Booked nights in [since, until] by group and days booked ahead. A booking-night counts once:
# its several sites are identical rows in one file, and quarter files overlap (as in
# area_night). Booked after the night (0.4% of rows) counts as booked on the day.
LEAD_COUNTS = text("""
WITH booked AS (
    SELECT DISTINCT n.area_id, n.night, n.reservation_id, n.booked_on,
           n.adults, n.children, n.infants, n.postcode, n.state
    FROM camp_night n
    JOIN camping_area a ON a.id = n.area_id
    WHERE a.campground_id = :campground_id AND n.night BETWEEN :since AND :until
)
SELECT CASE WHEN d.holiday IS NOT NULL THEN d.holiday
            WHEN extract(isodow FROM b.night) IN (5, 6) THEN 'weekend'
            ELSE 'weeknight' END AS "group",
       greatest(b.night - b.booked_on, 0) AS lead_days,
       count(*)::int AS nights
FROM booked b
JOIN calendar_day d ON d.night = b.night
GROUP BY 1, 2
""")


# Booked sites by month, from area_night like the calendar: the service decides which months
# count as history.
MONTHLY_SITES = text("""
SELECT date_trunc('month', n.night)::date AS month, sum(n.sites)::int AS sites
FROM area_night n
JOIN camping_area a ON a.id = n.area_id
WHERE a.campground_id = :campground_id
GROUP BY 1
""")


# Every campground with a booked night in [first, last], and its campers per night: the same
# filter, so each campers row has its campground.
BOOKED_CAMPGROUNDS = text("""
SELECT c.id, c.name, c.lat, c.lon
FROM campground c
WHERE EXISTS (
    SELECT 1 FROM area_night n JOIN camping_area a ON a.id = n.area_id
    WHERE a.campground_id = c.id AND n.night BETWEEN :first AND :last
)
ORDER BY c.id
""")
CAMPERS_BY_NIGHT = text("""
SELECT a.campground_id, n.night, sum(n.campers)::int AS campers
FROM area_night n
JOIN camping_area a ON a.id = n.area_id
WHERE n.night BETWEEN :first AND :last
GROUP BY 1, 2
""")


class CampgroundRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, campground_id: int) -> Campground | None:
        return await self._session.get(Campground, campground_id)

    async def calendar(self, campground_id: int, year: int) -> list[CalendarNight]:
        result = await self._session.execute(
            CALENDAR,
            {
                "campground_id": campground_id,
                "first": date(year, 1, 1),
                "next": date(year + 1, 1, 1),
                "min_history": MIN_HISTORY,
            },
        )
        return [CalendarNight(**row) for row in result.mappings()]

    async def history_end(self) -> date | None:
        return await self._session.scalar(text(HISTORY_END))

    async def lead_counts(self, campground_id: int, since: date, until: date) -> list[LeadCount]:
        result = await self._session.execute(
            LEAD_COUNTS, {"campground_id": campground_id, "since": since, "until": until}
        )
        return [LeadCount(**row) for row in result.mappings()]

    async def monthly_sites(self, campground_id: int) -> list[MonthSites]:
        result = await self._session.execute(MONTHLY_SITES, {"campground_id": campground_id})
        return [MonthSites(**row) for row in result.mappings()]

    async def booked_campgrounds(self, first: date, last: date) -> list[YearCampground]:
        result = await self._session.execute(BOOKED_CAMPGROUNDS, {"first": first, "last": last})
        return [YearCampground(**row) for row in result.mappings()]

    async def campers_by_night(self, first: date, last: date) -> list[NightCampers]:
        result = await self._session.execute(CAMPERS_BY_NIGHT, {"first": first, "last": last})
        return [NightCampers(**row) for row in result.mappings()]
