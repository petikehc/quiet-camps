from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from quiet_camps.api.campground_service import CalendarNight
from quiet_camps.api.queries import MIN_HISTORY
from quiet_camps.db.models import Campground

# Every night of the year for one campground (none if it doesn't exist): its typical night
# from campground_typical, as the search reads it, and the sites actually booked. Booked
# sites stop where the history does: the latest quarter isn't complete yet (ADR 0002).
CALENDAR = text("""
WITH history AS (
    SELECT (date_trunc('quarter', max(last_night)) - interval '1 day')::date AS last
    FROM campground
),
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
