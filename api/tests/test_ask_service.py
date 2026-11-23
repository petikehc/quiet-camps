"""Reading plain words, on its own: a fake reader stands in for the model."""

import asyncio
from datetime import date

from quiet_camps.api.ask_service import Answer, Holiday, Reading, ask
from quiet_camps.api.place_service import Place

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
