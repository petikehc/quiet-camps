from dataclasses import dataclass
from datetime import date, timedelta
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


HISTORY_YEARS = 3  # lead times doubled after 2020: describe how people book now
WEEKS = (0, 1, 2, 4, 8, 13, 26, 52)  # "booked by N weeks before"
LAST_GROUPS = ("weekend", "weeknight")  # after the holidays, which sort by name


@dataclass(frozen=True, kw_only=True)
class LeadCount:
    """How many booked nights in a group were booked lead_days before the night."""

    group: str  # a holiday, "weekend" (Friday and Saturday nights) or "weeknight"
    lead_days: int
    nights: int


@dataclass(frozen=True, kw_only=True)
class BookedBy:
    weeks: int
    share: float  # of the group's booked nights, booked at least `weeks` weeks before


@dataclass(frozen=True, kw_only=True)
class LeadTimeGroup:
    group: str
    nights: int
    booked_by: list[BookedBy]


@dataclass(frozen=True, kw_only=True)
class LeadTime:
    campground_id: int
    since: date | None  # None: no history at all
    until: date | None
    groups: list[LeadTimeGroup]


class LeadTimeSource(CampgroundSource, Protocol):
    async def history_end(self) -> date | None: ...

    async def lead_counts(
        self, campground_id: int, since: date, until: date
    ) -> list[LeadCount]: ...


def lead_time_group(group: str, counts: list[LeadCount]) -> LeadTimeGroup:
    nights = sum(c.nights for c in counts)
    booked_by = [
        BookedBy(
            weeks=weeks,
            share=sum(c.nights for c in counts if c.lead_days >= weeks * 7) / nights,
        )
        for weeks in WEEKS
    ]
    return LeadTimeGroup(group=group, nights=nights, booked_by=booked_by)


def group_order(group: str) -> tuple[int, str]:
    return (LAST_GROUPS.index(group) + 1 if group in LAST_GROUPS else 0, group)


async def campground_lead_time(source: LeadTimeSource, campground_id: int) -> LeadTime:
    if await source.get(campground_id) is None:
        raise CampgroundNotFound(campground_id)

    until = await source.history_end()
    if until is None:
        return LeadTime(campground_id=campground_id, since=None, until=None, groups=[])
    # The history ends on a quarter's last day, which every year has: no 29 February.
    since = until.replace(year=until.year - HISTORY_YEARS) + timedelta(days=1)

    by_group: dict[str, list[LeadCount]] = {}
    for count in await source.lead_counts(campground_id, since, until):
        by_group.setdefault(count.group, []).append(count)
    groups = [lead_time_group(g, by_group[g]) for g in sorted(by_group, key=group_order)]
    return LeadTime(campground_id=campground_id, since=since, until=until, groups=groups)
