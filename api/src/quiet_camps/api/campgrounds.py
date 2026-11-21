from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from quiet_camps.api.campground_repository import CampgroundRepository
from quiet_camps.api.campground_service import (
    CalendarSource,
    CampgroundSource,
    LeadTimeSource,
    YearsSource,
    campground_calendar,
    campground_lead_time,
    campground_years,
    get_campground,
)
from quiet_camps.api.db import get_session
from quiet_camps.api.problems import INVALID, NOT_FOUND
from quiet_camps.db.derived import FIRST_NIGHT, YEARS_AHEAD

campground_router = APIRouter(prefix="/campgrounds", responses={**INVALID, **NOT_FOUND})


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


class BookedByOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    weeks: int
    share: float  # of the group's booked nights, booked at least `weeks` weeks before


class LeadTimeGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    group: str  # a holiday, "weekend" (Friday and Saturday nights) or "weeknight"
    nights: int  # booked nights behind the shares: few means a rough answer
    booked_by: list[BookedByOut]  # 0, 1, 2, 4, 8, 13, 26 and 52 weeks


class LeadTimeOut(BaseModel):
    """How far ahead nights were booked, over the last 3 years of history."""

    model_config = ConfigDict(from_attributes=True)

    campground_id: int
    since: date | None  # None: no history at all
    until: date | None
    groups: list[LeadTimeGroupOut]  # holidays by name, then weekend, then weeknight


class YearMonthOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    month: int  # 1-12
    sites: int | None  # booked site-nights; None before the first booking or after `through`


class YearSitesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    year: int
    months: list[YearMonthOut]  # always 12


class YearsOut(BaseModel):
    """Booked sites by month, every year from the first booking: one line per year."""

    model_config = ConfigDict(from_attributes=True)

    campground_id: int
    through: date | None  # the end of history: the latest quarter isn't complete yet
    years: list[YearSitesOut]


def get_source(session: Annotated[AsyncSession, Depends(get_session)]) -> CampgroundSource:
    return CampgroundRepository(session)


def get_calendar_source(session: Annotated[AsyncSession, Depends(get_session)]) -> CalendarSource:
    return CampgroundRepository(session)


def get_lead_time_source(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LeadTimeSource:
    return CampgroundRepository(session)


def get_years_source(session: Annotated[AsyncSession, Depends(get_session)]) -> YearsSource:
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


@campground_router.get("/{campground_id}/lead-time")
async def campground_lead_time_by_group(
    campground_id: Annotated[int, Path(ge=1)],
    source: Annotated[LeadTimeSource, Depends(get_lead_time_source)],
) -> LeadTimeOut:
    found = await campground_lead_time(source, campground_id)
    return LeadTimeOut.model_validate(found)


@campground_router.get("/{campground_id}/years")
async def campground_years_by_month(
    campground_id: Annotated[int, Path(ge=1)],
    source: Annotated[YearsSource, Depends(get_years_source)],
) -> YearsOut:
    found = await campground_years(source, campground_id)
    return YearsOut.model_validate(found)
