"""A year of camping trips, from each camper's home postcode to the campground."""

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from quiet_camps.api.campground_service import (
    HolidayNight,
    HolidaySpan,
    holiday_spans,
    year_span,
)


@dataclass(frozen=True, kw_only=True)
class Arrivals:
    """Sites arriving on one night at one campground from one postcode."""

    night: date
    campground_id: int
    postcode: str | None
    overseas: bool  # from outside Australia, or a state nobody could tell
    sites: int


@dataclass(frozen=True, kw_only=True)
class Origin:
    postcode: str
    lat: float
    lon: float


@dataclass(frozen=True, kw_only=True)
class TripCampground:
    id: int
    name: str
    lat: float
    lon: float


@dataclass(kw_only=True)
class LeftOut:
    """Trips with no line to draw, in sites."""

    overseas: int = 0
    no_postcode: int = 0
    no_centroid: int = 0  # PO-box and university postcodes have no postal area
    unlocated: int = 0  # the campground has no location yet


@dataclass(frozen=True, kw_only=True)
class YearTrips:
    year: int
    first_night: date
    nights: int  # 365 or 366, fewer in the year the history ends
    origins: list[Origin]  # in the order they first appear
    campgrounds: list[TripCampground]  # in the order they first appear
    # Columns, one entry per arrival, in night order. per_night says how many entries each
    # night has, so there's no night column.
    per_night: list[int]
    origin: list[int]  # an index into origins
    campground: list[int]  # an index into campgrounds
    sites: list[int]
    left_out: LeftOut
    holidays: list[HolidaySpan]  # in night order: the year's peaks have names


class TripSource(Protocol):
    async def history_end(self) -> date | None: ...

    async def arrivals(self, first: date, last: date) -> list[Arrivals]: ...

    async def origins(self) -> list[Origin]: ...

    async def located_campgrounds(self) -> list[TripCampground]: ...

    async def holiday_nights(self, first: date, last: date) -> list[HolidayNight]: ...


async def year_trips(source: TripSource, year: int) -> YearTrips:
    first, last = year_span(year, await source.history_end())
    nights = (last - first).days + 1
    centres = {o.postcode: o for o in await source.origins()}
    places = {c.id: c for c in await source.located_campgrounds()}

    origin_index: dict[str, int] = {}
    campground_index: dict[int, int] = {}
    per_night = [0] * nights
    origin: list[int] = []
    campground: list[int] = []
    sites: list[int] = []
    left_out = LeftOut()
    for a in await source.arrivals(first, last):
        if a.overseas:
            left_out.overseas += a.sites
        elif a.postcode is None:
            left_out.no_postcode += a.sites
        elif a.postcode not in centres:
            left_out.no_centroid += a.sites
        elif a.campground_id not in places:
            left_out.unlocated += a.sites
        else:
            per_night[(a.night - first).days] += 1
            origin.append(origin_index.setdefault(a.postcode, len(origin_index)))
            campground.append(campground_index.setdefault(a.campground_id, len(campground_index)))
            sites.append(a.sites)
    return YearTrips(
        year=year,
        first_night=first,
        nights=nights,
        origins=[centres[p] for p in origin_index],
        campgrounds=[places[c] for c in campground_index],
        per_night=per_night,
        origin=origin,
        campground=campground,
        sites=sites,
        left_out=left_out,
        holidays=holiday_spans(await source.holiday_nights(first, last), first),
    )
