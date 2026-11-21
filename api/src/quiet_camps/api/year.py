"""GET /year/{year}: every campground's campers per night, for the 3D time-lapse."""

import hashlib
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from quiet_camps.api.campground_repository import CampgroundRepository
from quiet_camps.api.campground_service import YearSource, year_campers
from quiet_camps.api.db import get_session
from quiet_camps.api.problems import INVALID, NOT_FOUND
from quiet_camps.db.derived import FIRST_NIGHT, YEARS_AHEAD

# The data only changes when `qc refresh` runs, about quarterly; after a day the browser asks
# again with If-None-Match and usually gets an empty 304.
CACHE_CONTROL = "public, max-age=86400"

year_router = APIRouter(responses={**INVALID, **NOT_FOUND})


class YearCampgroundOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    lat: float | None  # None: not located yet; the time-lapse can't place it
    lon: float | None


class YearOut(BaseModel):
    """Campers per campground per night: one flat array, ready for a typed array on the GPU."""

    model_config = ConfigDict(from_attributes=True)

    year: int
    first_night: date
    nights: int  # 365 or 366, fewer in the year the history ends
    campgrounds: list[YearCampgroundOut]  # every campground booked that year, in id order
    values: list[int]  # campers: values[campground * nights + night], row by row


def get_year_source(session: Annotated[AsyncSession, Depends(get_session)]) -> YearSource:
    return CampgroundRepository(session)


def etag_matches(if_none_match: str | None, etag: str) -> bool:
    """If-None-Match holds one or more tags, or *; it matches by the weak comparison."""
    if if_none_match is None:
        return False
    tags = {tag.strip().removeprefix("W/") for tag in if_none_match.split(",")}
    return "*" in tags or etag.removeprefix("W/") in tags


@year_router.get(
    "/year/{year}",
    response_model=YearOut,
    responses={304: {"description": "Not Modified: the If-None-Match ETag still matches"}},
)
async def campers_by_night(
    # Later years than the calendar holds have no history; this also keeps date() in range.
    year: Annotated[int, Path(ge=FIRST_NIGHT.year, le=date.today().year + YEARS_AHEAD)],
    source: Annotated[YearSource, Depends(get_year_source)],
    if_none_match: Annotated[str | None, Header()] = None,
) -> Response:
    found = await year_campers(source, year)
    # Serialised here rather than by FastAPI, because the ETag is a hash of the body.
    body = YearOut.model_validate(found).model_dump_json().encode()
    # Weak: gzip changes the bytes on the wire, not what they mean.
    etag = f'W/"{hashlib.sha256(body).hexdigest()[:32]}"'
    headers = {"ETag": etag, "Cache-Control": CACHE_CONTROL}
    if etag_matches(if_none_match, etag):
        return Response(status_code=304, headers=headers)
    return Response(body, media_type="application/json", headers=headers)
