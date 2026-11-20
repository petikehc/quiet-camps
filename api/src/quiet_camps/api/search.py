from datetime import date
from typing import Annotated, Self

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from quiet_camps.api.db import get_session
from quiet_camps.api.queries import search_quiet

MAX_NIGHTS = 60

search_router = APIRouter()


class SearchParams(BaseModel):
    arrive: date
    depart: date
    park: str | None = None
    limit: int = Field(20, ge=1, le=100)

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


class SearchPage(BaseModel):
    """A wrapper, not a bare list, so 9c can add a `next` cursor without breaking clients."""

    results: list[QuietCampgroundOut]


@search_router.get("/campgrounds/quiet")
async def quiet_campgrounds(
    params: Annotated[SearchParams, Query()],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SearchPage:
    found = await search_quiet(session, params.arrive, params.depart, params.park, params.limit)
    return SearchPage(results=[QuietCampgroundOut.model_validate(c) for c in found])
