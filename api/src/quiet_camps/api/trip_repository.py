from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from quiet_camps.api.campground_repository import HISTORY_END
from quiet_camps.api.trip_service import Arrivals, Origin, TripCampground

# camp_night has a row per site per night. A trip is a stay: a run of consecutive nights at
# one campground under one booking (the same postcode, state, booked_on and reservation_id).
#
# 1. booking_night: overlapping quarterly files repeat whole stays, so each booking-night
#    keeps its larger copy, as area_night does (see its migration).
# 2. island: gaps and islands. Number a booking's nights in order; across a run of
#    consecutive nights, night minus that number stays the same, and a gap changes it.
#    dense_rank, because two bookings from one postcode on one day can share a night.
# 3. stay: one row per run, arriving on its first night, with its sites per night.
ARRIVALS = text("""
WITH per_file AS (
    SELECT a.campground_id, n.area_id, n.night, n.reservation_id, n.booked_on,
           n.adults, n.children, n.infants, n.postcode, n.state, count(*) AS sites
    FROM camp_night n
    JOIN camping_area a ON a.id = n.area_id
    WHERE n.night BETWEEN :since AND :last
    GROUP BY a.campground_id, n.area_id, n.night, n.reservation_id, n.booked_on,
             n.adults, n.children, n.infants, n.postcode, n.state, n.source_file
), booking_night AS (
    SELECT campground_id, night, reservation_id, booked_on, postcode, state,
           max(sites) AS sites
    FROM per_file
    GROUP BY campground_id, area_id, night, reservation_id, booked_on,
             adults, children, infants, postcode, state
), island AS (
    SELECT *, night - dense_rank() OVER (
        PARTITION BY campground_id, postcode, state, booked_on, reservation_id
        ORDER BY night
    )::int AS run
    FROM booking_night
), stay AS (
    SELECT campground_id, postcode, state, min(night) AS night,
           round(sum(sites)::numeric / count(DISTINCT night))::int AS sites
    FROM island
    GROUP BY campground_id, postcode, state, booked_on, reservation_id, run
)
SELECT night, campground_id, postcode, state IN ('OVERSEAS', 'UNKNOWN') AS overseas,
       sum(sites)::int AS sites
FROM stay
WHERE night >= :first
GROUP BY 1, 2, 3, 4
ORDER BY 1, 2, 3
""")
# Stays that began before the year started are read from this far back, so they aren't
# counted as arriving on 1 January. Longer stays than this are very rare.
LOOK_BACK = timedelta(days=31)

ORIGINS = text("SELECT postcode, lat, lon FROM postcode_centroid")
LOCATED_CAMPGROUNDS = text("SELECT id, name, lat, lon FROM campground WHERE lat IS NOT NULL")


class TripRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def history_end(self) -> date | None:
        return await self._session.scalar(text(HISTORY_END))

    async def arrivals(self, first: date, last: date) -> list[Arrivals]:
        result = await self._session.execute(
            ARRIVALS, {"since": first - LOOK_BACK, "first": first, "last": last}
        )
        return [Arrivals(**row) for row in result.mappings()]

    async def origins(self) -> list[Origin]:
        result = await self._session.execute(ORIGINS)
        return [Origin(**row) for row in result.mappings()]

    async def located_campgrounds(self) -> list[TripCampground]:
        result = await self._session.execute(LOCATED_CAMPGROUNDS)
        return [TripCampground(**row) for row in result.mappings()]
