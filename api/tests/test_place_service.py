"""Matching a place by name, on its own: a list stands in for the database."""

import asyncio

from quiet_camps.api.place_service import Place, find_place, matches

SUNSHINE_COAST = Place(name="Sunshine Coast", kind="council", lat=-26.65, lon=152.96)
SUNSHINE_BEACH = Place(name="Sunshine Beach", kind="locality", lat=-26.41, lon=153.10)
NOOSA = Place(name="Noosa", kind="council", lat=-26.39, lon=152.98)
NOOSA_CAMP = Place(name="Noosa", kind="campground", lat=-26.2, lon=153.0)
NOOSA_HEADS = Place(name="Noosa Heads", kind="locality", lat=-26.40, lon=153.09)
TOOWOOMBA = Place(name="Toowoomba", kind="council", lat=-27.56, lon=151.95)
PLACES = [SUNSHINE_BEACH, NOOSA_CAMP, NOOSA_HEADS, TOOWOOMBA, SUNSHINE_COAST, NOOSA]


class FakePlaces:
    async def places(self) -> list[Place]:
        return PLACES


def find(name: str) -> Place | None:
    return asyncio.run(find_place(FakePlaces(), name))


def test_a_loose_name_finds_the_place_meant() -> None:
    assert find("sunny coast") == SUNSHINE_COAST
    assert find("TOOWOOMBA") == TOOWOOMBA


def test_of_equal_matches_the_broader_place_comes_first() -> None:
    # All three hold the word: the council, then the suburb, then the campground.
    assert [m.place for m in matches(PLACES, "noosa", 3)] == [NOOSA, NOOSA_HEADS, NOOSA_CAMP]


def test_a_name_that_matches_nothing_well_is_no_place() -> None:
    assert find("tweed") is None  # nothing near 80
