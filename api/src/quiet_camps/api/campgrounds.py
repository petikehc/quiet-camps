from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from quiet_camps.api.campground_repository import CampgroundRepository
from quiet_camps.api.campground_service import CampgroundSource, get_campground
from quiet_camps.api.db import get_session

campground_router = APIRouter(prefix="/campgrounds")


class CampgroundOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    park_name: str
    last_night: date | None
    active: bool
    lat: float | None
    lon: float | None
    location_source: str | None
    location_flags: list[str]


def get_source(session: Annotated[AsyncSession, Depends(get_session)]) -> CampgroundSource:
    return CampgroundRepository(session)


@campground_router.get("/{campground_id}")
async def campground_by_id(
    campground_id: Annotated[int, Path(ge=1)],
    source: Annotated[CampgroundSource, Depends(get_source)],
) -> CampgroundOut:
    detail = await get_campground(source, campground_id)
    return CampgroundOut.model_validate(detail)
