"""The campground repository against the seeded search database."""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from quiet_camps.api.campground_repository import CampgroundRepository
from quiet_camps.api.campground_service import CampgroundSource
from quiet_camps.api.settings import Settings
from quiet_camps.db.models import Campground

QUIET = "Quiet Creek camping area"


async def quiet_creek_id(session: AsyncSession) -> int:
    found = await session.scalar(select(Campground.id).where(Campground.name == QUIET))
    assert found is not None
    return found


async def get(settings: Settings, campground_id: int | None = None) -> Campground | None:
    """Fetch through the repository in a fresh session; None looks up Quiet Creek's id."""
    engine = create_async_engine(settings.database_url)
    try:
        if campground_id is None:
            async with AsyncSession(engine) as session:
                campground_id = await quiet_creek_id(session)
        async with AsyncSession(engine) as session:
            # pyright checks here that the real repository fits what the service asks for.
            source: CampgroundSource = CampgroundRepository(session)
            return await source.get(campground_id)
    finally:
        await engine.dispose()


def test_gets_a_campground_by_id(seeded_settings: Settings) -> None:
    found = asyncio.run(get(seeded_settings))

    assert found is not None
    assert found.name == QUIET
    assert found.park_name == "Test Range National Park"


def test_an_unknown_id_is_none(seeded_settings: Settings) -> None:
    assert asyncio.run(get(seeded_settings, 999_999)) is None
