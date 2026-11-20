from sqlalchemy.ext.asyncio import AsyncSession

from quiet_camps.db.models import Campground


class CampgroundRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, campground_id: int) -> Campground | None:
        return await self._session.get(Campground, campground_id)
