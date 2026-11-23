"""GET /trips/{year}: every camping trip of a year, home to campground, for the homepage."""

import hashlib
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from quiet_camps.api.db import get_session
from quiet_camps.api.problems import INVALID, NOT_FOUND
from quiet_camps.api.trip_repository import TripRepository
from quiet_camps.api.trip_service import TripSource, year_trips
from quiet_camps.api.year import CACHE_CONTROL, HolidayOut, etag_matches
from quiet_camps.db.derived import FIRST_NIGHT, YEARS_AHEAD

trips_router = APIRouter(responses={**INVALID, **NOT_FOUND})


class OriginOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    postcode: str
    lat: float  # the postal area's centre (ABS ASGS 2021)
    lon: float


class TripCampgroundOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    lat: float
    lon: float


class LeftOutOut(BaseModel):
    """Trips with no line to draw, in sites."""

    model_config = ConfigDict(from_attributes=True)

    overseas: int  # or a state nobody could tell
    no_postcode: int
    no_centroid: int  # PO-box and university postcodes have no postal area
    unlocated: int  # the campground has no location yet


class TripsOut(BaseModel):
    """Arrivals as columns in night order: entry i is origin[i] → campground[i], sites[i].

    A trip is a stay, a run of nights under one booking, and arrives on its first night.
    Arrivals on one night from one postcode to one campground are one entry.
    """

    model_config = ConfigDict(from_attributes=True)

    year: int
    first_night: date
    nights: int  # 365 or 366, fewer in the year the history ends
    origins: list[OriginOut]
    campgrounds: list[TripCampgroundOut]
    per_night: list[int]  # entries on each night: the first per_night[0] are night 0's
    origin: list[int]  # an index into origins
    campground: list[int]  # an index into campgrounds
    sites: list[int]
    left_out: LeftOutOut
    holidays: list[HolidayOut]  # public holidays and their long weekends; Christmas twice


def get_trip_source(session: Annotated[AsyncSession, Depends(get_session)]) -> TripSource:
    return TripRepository(session)


@trips_router.get(
    "/trips/{year}",
    response_model=TripsOut,
    responses={304: {"description": "Not Modified: the If-None-Match ETag still matches"}},
)
async def trips_by_night(
    year: Annotated[int, Path(ge=FIRST_NIGHT.year, le=date.today().year + YEARS_AHEAD)],
    source: Annotated[TripSource, Depends(get_trip_source)],
    if_none_match: Annotated[str | None, Header()] = None,
) -> Response:
    found = await year_trips(source, year)
    # As /year: serialised here, because the ETag is a hash of the body.
    body = TripsOut.model_validate(found).model_dump_json().encode()
    etag = f'W/"{hashlib.sha256(body).hexdigest()[:32]}"'
    headers = {"ETag": etag, "Cache-Control": CACHE_CONTROL}
    if etag_matches(if_none_match, etag):
        return Response(status_code=304, headers=headers)
    return Response(body, media_type="application/json", headers=headers)
