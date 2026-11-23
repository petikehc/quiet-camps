import base64
import json
from datetime import date
from typing import Annotated, Self

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from quiet_camps.api.campground_repository import HOLIDAY_NIGHTS
from quiet_camps.api.campground_service import HolidayNight, holiday_spans
from quiet_camps.api.db import get_session
from quiet_camps.api.problems import INVALID
from quiet_camps.api.queries import After, Near, area_year, search_quiet
from quiet_camps.api.year import HolidayOut
from quiet_camps.db.derived import FIRST_NIGHT, YEARS_AHEAD

MAX_NIGHTS = 60
NEAR_KM = (10, 400)  # from the next town over to a long drive

search_router = APIRouter(responses=INVALID)


def encode_cursor(after: After) -> str:
    """Opaque to clients, so the paging can change without breaking them."""
    position = [after.busyness, after.peak, after.id]
    return base64.urlsafe_b64encode(json.dumps(position).encode()).decode()


def decode_cursor(cursor: str) -> After:
    try:
        busyness, peak, campground_id = json.loads(base64.urlsafe_b64decode(cursor))
        return After(float(busyness), float(peak), int(campground_id))
    except (ValueError, TypeError) as e:  # bad base64 or JSON, or not 3 numbers
        raise ValueError("after must be a `next` from a previous page") from e


class PlaceFilters(BaseModel):
    """Which campgrounds: the search and the year view share these, and their rules."""

    park: str | None = None
    q: str | None = Field(None, min_length=2, max_length=100)  # part of a name or park name
    # Within within_km of a place (from GET /places): all three, or none.
    near_lat: float | None = Field(None, ge=-45, le=-9)  # Australia's latitudes
    near_lon: float | None = Field(None, ge=112, le=155)
    within_km: float | None = Field(None, ge=NEAR_KM[0], le=NEAR_KM[1])

    @model_validator(mode="after")
    def check_near_is_whole(self) -> Self:
        given = [v is not None for v in (self.near_lat, self.near_lon, self.within_km)]
        if any(given) and not all(given):
            raise ValueError("near_lat, near_lon and within_km go together")
        return self

    def near(self) -> Near | None:
        if self.near_lat is None or self.near_lon is None or self.within_km is None:
            return None
        return Near(self.near_lat, self.near_lon, self.within_km)


class QuietFilters(PlaceFilters):
    """What to search for: the search's pages and its map share these, and their rules."""

    arrive: date
    depart: date

    @model_validator(mode="after")
    def check_depart_after_arrive(self) -> Self:
        if self.depart <= self.arrive:
            raise ValueError("depart must be after arrive")

        if (self.depart - self.arrive).days > MAX_NIGHTS:
            raise ValueError(f"booking must be {MAX_NIGHTS} nights at most")
        return self


class SearchParams(QuietFilters):
    limit: int = Field(20, ge=1, le=100)
    after: str | None = None  # the previous page's `next`; send the same filters with it

    @field_validator("after")
    @classmethod
    def check_cursor(cls, after: str | None) -> str | None:
        if after is not None:
            decode_cursor(after)  # a bad cursor is a 422, not a 500 in the route
        return after


class QuietCampgroundOut(BaseModel):
    """One campground in a search: how busy it usually is on the nights asked for."""

    # Built from the QuietCampground dataclass, which has attributes, not keys.
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    park_name: str
    busyness: float  # 1.0 = as busy as its own busiest nights; can go above 1
    typical_sites: float
    history: int  # past nights behind the thinnest typical night
    # Its busy night: the 95th percentile of its open nights, in sites. 1 or less is a
    # campground that's rarely booked at all, so 0% says little about it.
    busy_night_sites: float = Field(validation_alias="peak")
    lat: float | None
    lon: float | None
    location_source: str | None
    location_flags: list[str]
    # The OpenStreetMap object it was matched to (node, way or relation), or the match that was
    # rejected when location_flags has rejected_osm. None when nothing on the map matched.
    osm_type: str | None
    osm_id: int | None
    distance_km: float | None  # straight-line, from the place searched near; None without one


class SearchPage(BaseModel):
    """A wrapper, not a bare list, so paging fields sit beside the results."""

    results: list[QuietCampgroundOut]
    next: str | None  # pass as `after` for the next page; None on the last page


@search_router.get("/campgrounds/quiet")
async def quiet_campgrounds(
    params: Annotated[SearchParams, Query()],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SearchPage:
    after = None if params.after is None else decode_cursor(params.after)
    # One more than asked for tells us whether another page exists, without a count query.
    found = await search_quiet(
        session,
        params.arrive,
        params.depart,
        params.park,
        params.q,
        params.limit + 1,
        after,
        params.near(),
    )
    shown = found[: params.limit]
    cursor = None
    if len(found) > params.limit:
        cursor = encode_cursor(After(shown[-1].busyness, shown[-1].peak, shown[-1].id))
    return SearchPage(results=[QuietCampgroundOut.model_validate(c) for c in shown], next=cursor)


class SearchMap(BaseModel):
    """Every result at once, in rank order: the list pages through a search, a map shows it all."""

    results: list[QuietCampgroundOut]


@search_router.get("/campgrounds/quiet/map")
async def quiet_campgrounds_map(
    filters: Annotated[QuietFilters, Query()],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SearchMap:
    # No limit: about 550 active campgrounds at most, ~25 KB gzipped.
    found = await search_quiet(
        session,
        filters.arrive,
        filters.depart,
        filters.park,
        filters.q,
        limit=None,
        near=filters.near(),
    )
    return SearchMap(results=[QuietCampgroundOut.model_validate(c) for c in found])


class YearParams(PlaceFilters):
    year: int = Field(ge=FIRST_NIGHT.year, le=date.today().year + YEARS_AHEAD)


class AreaYearOut(BaseModel):
    """Each night of a year, how busy the chosen campgrounds usually are: for picking dates."""

    year: int
    first_night: date
    nights: int
    # The mean of their typical busyness, over those usually open that night (1.0 = as busy
    # as their own busiest nights); None when none are.
    busyness: list[float | None]
    open: list[int]  # how many of them are usually open each night
    holidays: list[HolidayOut]  # public holidays and their long weekends; Christmas twice


@search_router.get("/campgrounds/quiet/year")
async def quiet_campgrounds_year(
    params: Annotated[YearParams, Query()],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AreaYearOut:
    first, last = date(params.year, 1, 1), date(params.year, 12, 31)
    nights = await area_year(session, first, last, params.park, params.q, params.near())
    holiday_rows = await session.execute(HOLIDAY_NIGHTS, {"first": first, "last": last})
    holidays = holiday_spans([HolidayNight(**row) for row in holiday_rows.mappings()], first)
    return AreaYearOut(
        year=params.year,
        first_night=first,
        nights=len(nights),
        busyness=[n.busyness for n in nights],
        open=[n.open for n in nights],
        holidays=[HolidayOut.model_validate(h) for h in holidays],
    )
