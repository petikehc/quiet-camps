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


@dataclass(frozen=True, kw_only=True)
class CalendarNight:
    night: date
    kind: str  # its kind of night: "week 10 6", "easter +1"
    holiday: str | None
    typical_sites: float | None  # None: usually closed then, or too little history
    busyness: float | None
    sites: int | None  # booked; None once the history ends (the latest quarter, the future)


@dataclass(frozen=True, kw_only=True)
class CampgroundCalendar:
    campground_id: int
    year: int
    nights: list[CalendarNight]


class CalendarSource(Protocol):
    async def calendar(self, campground_id: int, year: int) -> list[CalendarNight]: ...


async def campground_calendar(
    source: CalendarSource, campground_id: int, year: int
) -> CampgroundCalendar:
    nights = await source.calendar(campground_id, year)
    # The route only asks for years the calendar holds, so no nights means no campground.
    if not nights:
        raise CampgroundNotFound(campground_id)
    return CampgroundCalendar(campground_id=campground_id, year=year, nights=nights)
