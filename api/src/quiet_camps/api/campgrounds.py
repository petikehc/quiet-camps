from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from quiet_camps.api.campground_repository import CampgroundRepository
from quiet_camps.api.campground_service import (
    CalendarSource,
    CampgroundSource,
    campground_calendar,
    get_campground,
)
from quiet_camps.api.db import get_session
from quiet_camps.db.derived import FIRST_NIGHT, YEARS_AHEAD

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


class CalendarNightOut(BaseModel):
    """One night: what's usual for its kind of night, and what was booked."""

    model_config = ConfigDict(from_attributes=True)

    night: date
    kind: str
    holiday: str | None
    typical_sites: float | None  # None: usually closed then, or too little history
    busyness: float | None  # 1.0 = as busy as its own busiest nights
    sites: int | None  # booked; None for the future and the latest, incomplete quarter


class CalendarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    campground_id: int
    year: int
    nights: list[CalendarNightOut]  # every night of the year, in order


def get_source(session: Annotated[AsyncSession, Depends(get_session)]) -> CampgroundSource:
    return CampgroundRepository(session)


def get_calendar_source(session: Annotated[AsyncSession, Depends(get_session)]) -> CalendarSource:
    return CampgroundRepository(session)


@campground_router.get("/{campground_id}")
async def campground_by_id(
    campground_id: Annotated[int, Path(ge=1)],
    source: Annotated[CampgroundSource, Depends(get_source)],
) -> CampgroundOut:
    detail = await get_campground(source, campground_id)
    return CampgroundOut.model_validate(detail)


@campground_router.get("/{campground_id}/calendar")
async def campground_calendar_by_year(
    campground_id: Annotated[int, Path(ge=1)],
    # The years calendar_day holds; `qc refresh` fills it to the same YEARS_AHEAD.
    year: Annotated[int, Query(ge=FIRST_NIGHT.year, le=date.today().year + YEARS_AHEAD)],
    source: Annotated[CalendarSource, Depends(get_calendar_source)],
) -> CalendarOut:
    found = await campground_calendar(source, campground_id, year)
    return CalendarOut.model_validate(found)
