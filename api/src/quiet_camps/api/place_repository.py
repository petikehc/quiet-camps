from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from quiet_camps.api.place_service import Place
from quiet_camps.api.queries import ACTIVE, ACTIVE_DAYS

# The ABS places, plus our active parks and located campgrounds. A park is where its
# campgrounds are on average.
PLACES = text(f"""
SELECT name, kind, lat, lon FROM place
UNION ALL
SELECT c.park_name, 'park', avg(c.lat), avg(c.lon) FROM campground c
WHERE c.lat IS NOT NULL AND {ACTIVE}
GROUP BY c.park_name
UNION ALL
SELECT c.name, 'campground', c.lat, c.lon FROM campground c
WHERE c.lat IS NOT NULL AND {ACTIVE}
""")


class PlaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def places(self) -> list[Place]:
        result = await self._session.execute(PLACES, {"active_days": ACTIVE_DAYS})
        return [Place(**row) for row in result.mappings()]
