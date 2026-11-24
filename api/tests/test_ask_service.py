"""Reading plain words, on its own: a fake reader stands in for the model."""

import asyncio
from datetime import date

from quiet_camps.api.ask_service import (
    Answer,
    Holiday,
    Reading,
    ask,
    coming_school_holidays,
    first_week,
    long_weekends,
)
from quiet_camps.api.place_service import Place
from quiet_camps.ingest.school_holidays import SchoolHoliday

TODAY = date(2026, 11, 23)  # a Monday
SUNSHINE_COAST = Place(name="Sunshine Coast", kind="council", lat=-26.65, lon=152.96)


class FakeReader:
    def __init__(self, reading: Reading) -> None:
        self.reading = reading

    async def read(self, text: str, today: date, holidays: list[Holiday]) -> Reading:
        return self.reading


class FakePlaces:
    async def places(self) -> list[Place]:
        return [SUNSHINE_COAST]


def read(**said: object) -> Answer:
    fields: dict[str, object] = {
        "arrive": None,
        "depart": None,
        "place": None,
        "place_role": None,
        "within_km": None,
    }
    reading = Reading.model_validate(fields | said)
    return asyncio.run(ask(FakeReader(reading), FakePlaces(), "words", TODAY, []))


def test_next_weekend_around_the_sunny_coast() -> None:
    answer = read(arrive="2026-11-27", depart="2026-11-29", place="Sunny Coast", place_role="near")

    assert (answer.arrive, answer.depart) == (date(2026, 11, 27), date(2026, 11, 29))
    assert answer.place == SUNSHINE_COAST
    assert (answer.place_role, answer.within_km) == ("near", 50)


def test_arriving_with_no_end_is_a_weekend() -> None:
    assert read(arrive="2026-12-04").depart == date(2026, 12, 6)


def test_a_stay_is_60_nights_at_most() -> None:
    assert read(arrive="2027-01-01", depart="2027-06-01").depart == date(2027, 3, 2)


def test_a_night_in_the_past_is_not_understood() -> None:
    answer = read(arrive="2026-11-20", depart="2026-11-22")

    assert (answer.arrive, answer.depart) == (None, None)


def test_from_home_looks_further_than_near_a_place() -> None:
    assert read(place="Sunshine Coast", place_role="from").within_km == 150


def test_a_distance_said_is_kept_within_10_to_400_km() -> None:
    assert read(place="Sunshine Coast", within_km=1000).within_km == 400
    assert read(place="Sunshine Coast", within_km=2).within_km == 10


def test_a_place_that_matches_nothing_is_said_back() -> None:
    answer = read(place="Tweed Heads", place_role="near")

    assert answer.place is None
    assert answer.place_asked == "Tweed Heads"
    assert answer.within_km is None  # no place to be near


def test_school_holidays_offer_their_first_week_from_the_first_saturday() -> None:
    """2026's summer holidays: the first day off is Saturday 12 December."""
    summer = SchoolHoliday(
        name="summer", first_night=date(2026, 12, 11), last_night=date(2027, 1, 25)
    )

    assert first_week(summer) == Holiday(
        name="summer school holidays, first week",
        arrive=date(2026, 12, 12),
        depart=date(2026, 12, 19),
    )


def test_a_school_holiday_starting_on_good_friday_starts_its_week_on_the_saturday() -> None:
    autumn = SchoolHoliday(
        name="autumn", first_night=date(2026, 4, 2), last_night=date(2026, 4, 18)
    )

    assert (first_week(autumn).arrive, first_week(autumn).depart) == (
        date(2026, 4, 4),
        date(2026, 4, 11),
    )


def test_only_coming_school_holidays_are_offered() -> None:
    spring = SchoolHoliday(
        name="spring", first_night=date(2026, 9, 18), last_night=date(2026, 10, 4)
    )
    summer = SchoolHoliday(
        name="summer", first_night=date(2026, 12, 11), last_night=date(2027, 1, 25)
    )
    far = SchoolHoliday(name="winter", first_night=date(2028, 6, 23), last_night=date(2028, 7, 8))

    coming = coming_school_holidays(date(2026, 11, 24), [spring, summer, far])

    assert [h.name for h in coming] == ["summer school holidays, first week"]


QLD_2026_27 = {
    date(2026, 12, 25): "Christmas Day",
    date(2026, 12, 26): "Boxing Day",
    date(2026, 12, 28): "Boxing Day (observed)",
    date(2027, 1, 1): "New Year's Day",
    date(2027, 1, 26): "Australia Day",
    date(2027, 8, 11): "The Royal Queensland Show",
}


def test_long_weekends_are_runs_of_three_or_more_days_off() -> None:
    weekends = long_weekends(date(2026, 11, 24), QLD_2026_27)

    assert [(w.name, w.arrive, w.depart) for w in weekends] == [
        # Christmas Day on a Friday, Boxing Day on Saturday and its Monday off: Thursday night
        # to Monday morning.
        ("Christmas Day long weekend", date(2026, 12, 24), date(2026, 12, 28)),
        ("New Year's Day long weekend", date(2026, 12, 31), date(2027, 1, 3)),
    ]


def test_a_midweek_holiday_is_not_a_long_weekend() -> None:
    """Australia Day 2027 is a Tuesday, the Ekka a Wednesday: one day off each."""
    names = [w.name for w in long_weekends(date(2027, 1, 5), QLD_2026_27)]

    assert names == []


def test_the_next_long_weekend_from_today_is_christmas() -> None:
    """From the real Queensland calendar, as /ask gives the model."""
    first = long_weekends(date(2026, 11, 24))[0]

    assert (first.arrive, first.depart) == (date(2026, 12, 24), date(2026, 12, 28))
