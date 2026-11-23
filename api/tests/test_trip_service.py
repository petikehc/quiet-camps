import asyncio
from datetime import date, timedelta

import pytest

from quiet_camps.api.campground_service import HolidayNight, HolidaySpan, NoHistory
from quiet_camps.api.trip_service import (
    Arrivals,
    LeftOut,
    Origin,
    TripCampground,
    year_trips,
)

BRISBANE = Origin(postcode="4000", lat=-27.47, lon=153.02)
TOWNSVILLE = Origin(postcode="4810", lat=-19.26, lon=146.82)
HOOP_PINES = TripCampground(id=3, name="Hoop Pines", lat=-28.3, lon=152.7)
TEEWAH = TripCampground(id=9, name="Teewah", lat=-26.2, lon=153.1)


class FakeTrips:
    """Satisfies TripSource: two postcodes, two located campgrounds, fixed arrivals."""

    def __init__(
        self,
        history_end: date | None,
        arrivals: list[Arrivals],
        holidays: list[HolidayNight] | None = None,
    ) -> None:
        self.end = history_end
        self.rows = arrivals
        self.holidays = holidays or []
        self.asked: tuple[date, date] | None = None
        self.asked_holidays: tuple[date, date] | None = None

    async def history_end(self) -> date | None:
        return self.end

    async def arrivals(self, first: date, last: date) -> list[Arrivals]:
        self.asked = (first, last)
        return self.rows

    async def origins(self) -> list[Origin]:
        return [BRISBANE, TOWNSVILLE]

    async def located_campgrounds(self) -> list[TripCampground]:
        return [HOOP_PINES, TEEWAH]

    async def holiday_nights(self, first: date, last: date) -> list[HolidayNight]:
        self.asked_holidays = (first, last)
        return self.holidays


def arrive(
    night: date,
    campground_id: int,
    postcode: str | None,
    sites: int = 1,
    overseas: bool = False,
) -> Arrivals:
    return Arrivals(
        night=night,
        campground_id=campground_id,
        postcode=postcode,
        overseas=overseas,
        sites=sites,
    )


def test_trips_are_columns_in_night_order() -> None:
    arrivals = [
        arrive(date(2025, 1, 1), 9, "4810", sites=2),
        arrive(date(2025, 1, 1), 3, "4000"),
        arrive(date(2025, 1, 3), 9, "4000", sites=5),
    ]

    found = asyncio.run(year_trips(FakeTrips(date(2025, 12, 31), arrivals), 2025))

    assert (found.first_night, found.nights) == (date(2025, 1, 1), 365)
    assert found.origins == [TOWNSVILLE, BRISBANE]  # in the order they first appear
    assert found.campgrounds == [TEEWAH, HOOP_PINES]
    assert found.per_night[:4] == [2, 0, 1, 0]
    assert sum(found.per_night) == 3
    assert found.origin == [0, 1, 1]
    assert found.campground == [0, 1, 0]
    assert found.sites == [2, 1, 5]
    assert found.left_out == LeftOut()


def test_trips_without_a_line_to_draw_are_counted_not_drawn() -> None:
    arrivals = [
        arrive(date(2025, 2, 1), 3, "8001", sites=2, overseas=True),
        arrive(date(2025, 2, 1), 3, None, sites=3),
        arrive(date(2025, 2, 1), 3, "4001", sites=4),  # a PO-box postcode: no centre
        arrive(date(2025, 2, 1), 77, "4000", sites=5),  # not located
        arrive(date(2025, 2, 1), 3, "4000"),
    ]

    found = asyncio.run(year_trips(FakeTrips(date(2025, 12, 31), arrivals), 2025))

    assert found.left_out == LeftOut(overseas=2, no_postcode=3, no_centroid=4, unlocated=5)
    assert (found.origins, found.campgrounds, found.sites) == ([BRISBANE], [HOOP_PINES], [1])


def test_holidays_are_spans_of_the_years_nights() -> None:
    easter = [
        HolidayNight(night=date(2025, 4, 17) + timedelta(days=i), holiday="easter")
        for i in range(4)
    ]
    source = FakeTrips(date(2025, 12, 31), [], easter)

    found = asyncio.run(year_trips(source, 2025))

    assert found.holidays == [HolidaySpan(name="easter", night=106, nights=4)]
    assert source.asked_holidays == (date(2025, 1, 1), date(2025, 12, 31))


def test_a_year_without_holidays_has_none() -> None:
    found = asyncio.run(year_trips(FakeTrips(date(2025, 12, 31), []), 2025))

    assert found.holidays == []


def test_the_year_history_ends_in_stops_there() -> None:
    source = FakeTrips(date(2026, 9, 30), [])

    found = asyncio.run(year_trips(source, 2026))

    assert found.nights == len(found.per_night) == 273
    assert source.asked == source.asked_holidays == (date(2026, 1, 1), date(2026, 9, 30))


@pytest.mark.parametrize("history_end", [date(2025, 12, 31), None])
def test_a_year_after_the_history_has_no_trips(history_end: date | None) -> None:
    with pytest.raises(NoHistory):
        asyncio.run(year_trips(FakeTrips(history_end, []), 2026))
