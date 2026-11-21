import base64
import json
from datetime import date
from typing import Annotated, Self

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from quiet_camps.api.db import get_session
from quiet_camps.api.problems import INVALID
from quiet_camps.api.queries import After, search_quiet

MAX_NIGHTS = 60

search_router = APIRouter(responses=INVALID)


def encode_cursor(after: After) -> str:
    """Opaque to clients, so the paging can change without breaking them."""
    return base64.urlsafe_b64encode(json.dumps([after.busyness, after.id]).encode()).decode()


def decode_cursor(cursor: str) -> After:
    try:
        busyness, campground_id = json.loads(base64.urlsafe_b64decode(cursor))
        return After(float(busyness), int(campground_id))
    except (ValueError, TypeError) as e:  # bad base64 or JSON, or not [number, number]
        raise ValueError("after must be a `next` from a previous page") from e


class SearchParams(BaseModel):
    arrive: date
    depart: date
    park: str | None = None
    q: str | None = Field(None, min_length=2, max_length=100)  # part of a name or park name
    limit: int = Field(20, ge=1, le=100)
    after: str | None = None  # the previous page's `next`; send the same filters with it

    @field_validator("after")
    @classmethod
    def check_cursor(cls, after: str | None) -> str | None:
        if after is not None:
            decode_cursor(after)  # a bad cursor is a 422, not a 500 in the route
        return after

    @model_validator(mode="after")
    def check_depart_after_arrive(self) -> Self:
        if self.depart <= self.arrive:
            raise ValueError("depart must be after arrive")

        if (self.depart - self.arrive).days > MAX_NIGHTS:
            raise ValueError(f"booking must be {MAX_NIGHTS} nights at most")
        return self


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
    lat: float | None
    lon: float | None
    location_source: str | None
    location_flags: list[str]
    # The OpenStreetMap object it was matched to (node, way or relation), or the match that was
    # rejected when location_flags has rejected_osm. None when nothing on the map matched.
    osm_type: str | None
    osm_id: int | None


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
        session, params.arrive, params.depart, params.park, params.q, params.limit + 1, after
    )
    shown = found[: params.limit]
    cursor = None
    if len(found) > params.limit:
        cursor = encode_cursor(After(shown[-1].busyness, shown[-1].id))
    return SearchPage(results=[QuietCampgroundOut.model_validate(c) for c in shown], next=cursor)
