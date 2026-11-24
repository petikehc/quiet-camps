"""The campground service on its own: a fake source stands in for the database."""

import asyncio
from datetime import date, timedelta

import pytest

from quiet_camps.api.campground_service import (
    CalendarNight,
    CampgroundCalendar,
    CampgroundDetail,
    CampgroundNotFound,
    HolidayNight,
    HolidaySpan,
    LeadCount,
    MonthSites,
    NightCampers,
    NoHistory,
    YearCampground,
    campground_calendar,
    campground_lead_time,
    campground_years,
    get_campground,
    year_campers,
)
from quiet_camps.db.models import Campground

HISTORY_END = date(2025, 9, 30)
A_YEAR_BEFORE = HISTORY_END - timedelta(days=365)


class FakeSource:
    """Satisfies CampgroundSource by shape alone: it never names it."""

    def __init__(self, *campgrounds: Campground) -> None:
        self.campgrounds = {c.id: c for c in campgrounds}

    async def get(self, campground_id: int) -> Campground | None:
        return self.campgrounds.get(campground_id)

    async def history_end(self) -> date | None:
        return HISTORY_END


def campground(campground_id: int = 7, last_night: date | None = date(2025, 3, 11)) -> Campground:
    # A transient ORM object: no session, no database.
    return Campground(
        id=campground_id,
        name="Quiet Creek camping area",
        park_name="Test Range National Park",
        last_night=last_night,
        lat=-28.2,
        lon=153.1,
        location_source="osm",
        location_flags=["weak_name"],
    )


def detail(*campgrounds: Campground, campground_id: int = 7) -> CampgroundDetail:
    return asyncio.run(get_campground(FakeSource(*campgrounds), campground_id))


def test_returns_the_campgrounds_fields() -> None:
    assert detail(campground()) == CampgroundDetail(
        id=7,
        name="Quiet Creek camping area",
        park_name="Test Range National Park",
        last_night=date(2025, 3, 11),
        active=True,
        lat=-28.2,
        lon=153.1,
        location_source="osm",
        location_flags=["weak_name"],
    )


def test_booked_in_the_year_before_the_history_ends_is_active() -> None:
    assert detail(campground(last_night=A_YEAR_BEFORE + timedelta(days=1))).active


def test_not_booked_for_a_year_before_the_history_ends_is_retired() -> None:
    assert not detail(campground(last_night=A_YEAR_BEFORE)).active


def test_never_booked_is_retired() -> None:
    assert not detail(campground(last_night=None)).active


def test_an_unknown_id_is_not_found() -> None:
    with pytest.raises(CampgroundNotFound) as raised:
        detail(campground(campground_id=7), campground_id=8)

    assert raised.value.campground_id == 8


class FakeCalendar:
    """Satisfies CalendarSource: the nights of one campground, any year."""

    def __init__(self, campground_id: int, nights: list[CalendarNight]) -> None:
        self.campground_id = campground_id
        self.nights = nights

    async def calendar(self, campground_id: int, year: int) -> list[CalendarNight]:
        return self.nights if campground_id == self.campground_id else []


NEW_YEAR = CalendarNight(
    night=date(2025, 1, 1),
    kind="new year",
    holiday="christmas",
    typical_sites=9.0,
    busyness=0.9,
    sites=11,
)


def test_a_calendar_is_its_nights() -> None:
    found = asyncio.run(campground_calendar(FakeCalendar(7, [NEW_YEAR]), 7, 2025))

    assert found == CampgroundCalendar(campground_id=7, year=2025, nights=[NEW_YEAR])


def test_no_nights_means_no_campground() -> None:
    with pytest.raises(CampgroundNotFound) as raised:
        asyncio.run(campground_calendar(FakeCalendar(7, [NEW_YEAR]), 8, 2025))

    assert raised.value.campground_id == 8


class FakeLeadTimes(FakeSource):
    """Satisfies LeadTimeSource: FakeSource's campgrounds, one history end, fixed counts."""

    def __init__(
        self, *campgrounds: Campground, history_end: date | None, counts: list[LeadCount]
    ) -> None:
        super().__init__(*campgrounds)
        self.end = history_end
        self.counts = counts
        self.asked: tuple[date, date] | None = None

    async def history_end(self) -> date | None:
        return self.end

    async def lead_counts(self, campground_id: int, since: date, until: date) -> list[LeadCount]:
        self.asked = (since, until)
        return self.counts


def test_lead_time_asks_for_the_last_3_years_of_history() -> None:
    source = FakeLeadTimes(campground(), history_end=date(2026, 9, 30), counts=[])

    found = asyncio.run(campground_lead_time(source, 7))

    assert source.asked == (date(2023, 10, 1), date(2026, 9, 30))
    assert (found.since, found.until) == (date(2023, 10, 1), date(2026, 9, 30))


def test_lead_time_shares_add_up_from_the_longest_lead() -> None:
    counts = [
        LeadCount(group="easter", lead_days=0, nights=1),
        LeadCount(group="easter", lead_days=30, nights=2),  # 4 weeks and 2 days
        LeadCount(group="easter", lead_days=200, nights=1),
    ]
    source = FakeLeadTimes(campground(), history_end=date(2026, 9, 30), counts=counts)

    [easter] = asyncio.run(campground_lead_time(source, 7)).groups

    assert easter.nights == 4
    assert [(b.weeks, b.share) for b in easter.booked_by] == [
        (0, 1.0),
        (1, 0.75),
        (2, 0.75),
        (4, 0.75),
        (8, 0.25),
        (13, 0.25),
        (26, 0.25),
        (52, 0.0),
    ]


def test_lead_time_groups_holidays_by_name_then_school_holidays_weekend_weeknight() -> None:
    counts = [
        LeadCount(group=g, lead_days=0, nights=1)
        for g in ("weeknight", "school holidays", "sovereign's birthday", "weekend", "christmas")
    ]
    source = FakeLeadTimes(campground(), history_end=date(2026, 9, 30), counts=counts)

    groups = asyncio.run(campground_lead_time(source, 7)).groups

    assert [g.group for g in groups] == [
        "christmas",
        "sovereign's birthday",  # after "school holidays" by name, but a holiday comes first
        "school holidays",
        "weekend",
        "weeknight",
    ]


def test_lead_time_without_any_history_is_empty() -> None:
    source = FakeLeadTimes(campground(), history_end=None, counts=[])

    found = asyncio.run(campground_lead_time(source, 7))

    assert (found.since, found.until, found.groups) == (None, None, [])
    assert source.asked is None


def test_lead_time_for_an_unknown_id_is_not_found() -> None:
    source = FakeLeadTimes(campground(), history_end=date(2026, 9, 30), counts=[])

    with pytest.raises(CampgroundNotFound):
        asyncio.run(campground_lead_time(source, 8))


class FakeYears(FakeSource):
    """Satisfies YearsSource: FakeSource's campgrounds, one history end, fixed months."""

    def __init__(
        self, *campgrounds: Campground, history_end: date | None, months: list[MonthSites]
    ) -> None:
        super().__init__(*campgrounds)
        self.end = history_end
        self.months = months

    async def history_end(self) -> date | None:
        return self.end

    async def monthly_sites(self, campground_id: int) -> list[MonthSites]:
        return self.months


def year_sites(source: FakeYears) -> dict[int, list[int | None]]:
    found = asyncio.run(campground_years(source, 7))
    return {y.year: [m.sites for m in y.months] for y in found.years}


def test_years_fill_months_between_the_first_booking_and_the_end_of_history() -> None:
    months = [
        MonthSites(month=date(2024, 11, 1), sites=3),
        MonthSites(month=date(2025, 2, 1), sites=5),
    ]
    source = FakeYears(campground(), history_end=date(2025, 3, 31), months=months)

    assert year_sites(source) == {
        2024: [None] * 10 + [3, 0],
        2025: [0, 5, 0] + [None] * 9,
    }


def test_years_leave_out_months_after_the_history() -> None:
    months = [
        MonthSites(month=date(2025, 3, 1), sites=1),
        MonthSites(month=date(2025, 4, 1), sites=9),
    ]
    source = FakeYears(campground(), history_end=date(2025, 3, 31), months=months)

    assert year_sites(source) == {2025: [None, None, 1] + [None] * 9}


def test_years_without_history_are_empty() -> None:
    later = [MonthSites(month=date(2025, 4, 1), sites=9)]  # only in the latest quarter

    assert year_sites(FakeYears(campground(), history_end=date(2025, 3, 31), months=later)) == {}
    assert year_sites(FakeYears(campground(), history_end=None, months=[])) == {}


def test_years_for_an_unknown_id_is_not_found() -> None:
    source = FakeYears(campground(), history_end=date(2025, 3, 31), months=[])

    with pytest.raises(CampgroundNotFound):
        asyncio.run(campground_years(source, 8))


class FakeYear:
    """Satisfies YearSource: two campgrounds and their campers, one history end."""

    def __init__(
        self,
        history_end: date | None,
        rows: list[NightCampers],
        holidays: list[HolidayNight] | None = None,
    ) -> None:
        self.end = history_end
        self.rows = rows
        self.holidays = holidays or []
        self.asked: tuple[date, date] | None = None
        self.asked_holidays: tuple[date, date] | None = None

    async def history_end(self) -> date | None:
        return self.end

    async def booked_campgrounds(self, first: date, last: date) -> list[YearCampground]:
        self.asked = (first, last)
        return [
            YearCampground(id=3, name="Hoop Pines", lat=-28.3, lon=152.7),
            YearCampground(id=9, name="Teewah", lat=None, lon=None),
        ]

    async def campers_by_night(self, first: date, last: date) -> list[NightCampers]:
        return self.rows

    async def holiday_nights(self, first: date, last: date) -> list[HolidayNight]:
        self.asked_holidays = (first, last)
        return self.holidays


def holiday_nights(name: str, first: date, count: int) -> list[HolidayNight]:
    return [HolidayNight(night=first + timedelta(days=i), holiday=name) for i in range(count)]


def test_a_year_is_flat_campground_by_campground() -> None:
    rows = [
        NightCampers(campground_id=9, night=date(2025, 1, 2), campers=7),
        NightCampers(campground_id=3, night=date(2025, 12, 31), campers=4),
    ]

    found = asyncio.run(year_campers(FakeYear(date(2025, 12, 31), rows), 2025))

    assert (found.first_night, found.nights) == (date(2025, 1, 1), 365)
    assert [c.id for c in found.campgrounds] == [3, 9]
    assert len(found.values) == 2 * 365
    assert found.values[364] == 4  # Hoop Pines, 31 December
    assert found.values[365 + 1] == 7  # Teewah, 2 January
    assert sum(found.values) == 11


def test_the_year_history_ends_in_stops_there() -> None:
    source = FakeYear(date(2026, 9, 30), [])

    found = asyncio.run(year_campers(source, 2026))

    assert found.nights == 273
    assert source.asked == (date(2026, 1, 1), date(2026, 9, 30))


@pytest.mark.parametrize("history_end", [date(2025, 12, 31), None])
def test_a_year_after_the_history_has_none(history_end: date | None) -> None:
    with pytest.raises(NoHistory) as raised:
        asyncio.run(year_campers(FakeYear(history_end, []), 2026))

    assert raised.value.year == 2026


def test_consecutive_holiday_nights_are_one_span() -> None:
    nights = holiday_nights("easter", date(2025, 4, 17), 4) + holiday_nights(
        "ekka", date(2025, 8, 12), 1
    )

    found = asyncio.run(year_campers(FakeYear(date(2025, 12, 31), [], nights), 2025))

    assert found.holidays == [
        HolidaySpan(name="easter", night=106, nights=4),  # 17 April is the 107th night
        HolidaySpan(name="ekka", night=223, nights=1),
    ]


def test_christmas_starts_and_ends_a_year_as_two_spans() -> None:
    nights = holiday_nights("christmas", date(2025, 1, 1), 4) + holiday_nights(
        "christmas", date(2025, 12, 26), 6
    )

    found = asyncio.run(year_campers(FakeYear(date(2025, 12, 31), [], nights), 2025))

    assert found.holidays == [
        HolidaySpan(name="christmas", night=0, nights=4),
        HolidaySpan(name="christmas", night=359, nights=6),
    ]


def test_holidays_side_by_side_stay_apart() -> None:
    nights = holiday_nights("anzac day", date(2025, 4, 24), 3) + holiday_nights(
        "labour day", date(2025, 4, 27), 2
    )

    found = asyncio.run(year_campers(FakeYear(date(2025, 12, 31), [], nights), 2025))

    assert [(h.name, h.nights) for h in found.holidays] == [("anzac day", 3), ("labour day", 2)]


def test_holidays_stop_where_the_history_does() -> None:
    source = FakeYear(date(2026, 9, 30), [])

    asyncio.run(year_campers(source, 2026))

    assert source.asked_holidays == (date(2026, 1, 1), date(2026, 9, 30))
