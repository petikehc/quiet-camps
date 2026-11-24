"""GET /places: Queensland places by name, for the place to search near."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from quiet_camps.api.db import get_session
from quiet_camps.api.place_repository import PlaceRepository
from quiet_camps.api.place_service import PlaceSource, search_places
from quiet_camps.api.problems import INVALID

places_router = APIRouter(responses=INVALID)


class PlaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    kind: str  # council, locality, park or campground
    lat: float
    lon: float


class PlacesOut(BaseModel):
    results: list[PlaceOut]  # best match first


def get_place_source(session: Annotated[AsyncSession, Depends(get_session)]) -> PlaceSource:
    return PlaceRepository(session)


@places_router.get("/places")
async def places(
    q: Annotated[str, Query(min_length=2, max_length=100)],
    source: Annotated[PlaceSource, Depends(get_place_source)],
    limit: Annotated[int, Query(ge=1, le=20)] = 8,
) -> PlacesOut:
    found = await search_places(source, q, limit)
    return PlacesOut(results=[PlaceOut.model_validate(m.place) for m in found])
