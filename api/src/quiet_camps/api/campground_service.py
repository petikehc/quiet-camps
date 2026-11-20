from dataclasses import dataclass
from datetime import date
from typing import Protocol

from quiet_camps.db.locations import ACTIVE_SINCE
from quiet_camps.db.models import Campground


class CampgroundSource(Protocol):
    async def get(self, campground_id: int) -> Campground | None: ...


class CampgroundNotFound(Exception):
    def __init__(self, campground_id: int) -> None:
        super().__init__(f"Campground not found: {campground_id}")
        self.campground_id = campground_id


@dataclass(frozen=True, kw_only=True)
class CampgroundDetail:
    id: int
    name: str
    park_name: str
    last_night: date | None
    active: bool
    lat: float | None
    lon: float | None
    location_source: str | None
    location_flags: list[str]


async def get_campground(source: CampgroundSource, campground_id: int) -> CampgroundDetail:
    campground = await source.get(campground_id=campground_id)
    if campground is None:
        raise CampgroundNotFound(campground_id=campground_id)

    active = False if campground.last_night is None else campground.last_night >= ACTIVE_SINCE

    return CampgroundDetail(
        id=campground.id,
        name=campground.name,
        park_name=campground.park_name,
        last_night=campground.last_night,
        active=active,
        lat=campground.lat,
        lon=campground.lon,
        location_source=campground.location_source,
        location_flags=campground.location_flags,
    )
