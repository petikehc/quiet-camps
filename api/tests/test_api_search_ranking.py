"""The search over a small seeded history, built once per test session by `seeded_client`."""

from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient

from quiet_camps.ingest.geo import km

SEARCH = "/campgrounds/quiet"
# The Saturday of ISO week 10 in 2027: compared with week-10 Saturdays in 2022-2025.
SATURDAY = {"arrive": "2027-03-13", "depart": "2027-03-14"}

BIG = "Big Hollow camping area"  # also 0 on these Saturdays, but its busy night is 20 sites
QUIET = "Quiet Creek camping area"
TWIN = "Twin Hollow camping area"  # the same history as QUIET: a tie at 0
MIDDLE = "Middle Creek camping area"
BUSY = "Busy Beach camping area"


def page(client: TestClient, **params: Any) -> dict[str, Any]:
    response = client.get(SEARCH, params={**SATURDAY, **params})
    assert response.status_code == 200
    return response.json()


def results(client: TestClient, **params: Any) -> list[dict[str, Any]]:
    return page(client, **params)["results"]


def names(client: TestClient, **params: Any) -> list[str]:
    return [c["name"] for c in results(client, **params)]


def test_quietest_comes_first(seeded_client: TestClient) -> None:
    found = results(seeded_client)

    assert found[0]["name"] == BIG  # equally quiet: the bigger campground first
    assert {c["name"] for c in found[1:3]} == {QUIET, TWIN}
    assert found[1]["id"] < found[2]["id"]  # the same size too: the lower id
    assert [c["name"] for c in found[3:]] == [MIDDLE, BUSY]


def test_a_result_says_how_big_its_busy_night_is(seeded_client: TestClient) -> None:
    found = {c["name"]: c for c in results(seeded_client)}

    assert found[BIG]["busy_night_sites"] == 20
    assert found[QUIET]["busy_night_sites"] == 0  # booked on 4 of its ~124 open nights


def test_busyness_is_against_each_campgrounds_own_busy_nights(seeded_client: TestClient) -> None:
    found = {c["name"]: c for c in results(seeded_client)}

    assert found[QUIET]["busyness"] == 0
    assert found[MIDDLE]["busyness"] == 2  # 2 sites; its busy night (p95) is under 1, so 1
    assert found[BUSY]["busyness"] == 10
    assert found[QUIET]["history"] == 4  # one week-10 Saturday a year, 2022-2025


def test_a_campground_closed_in_march_is_left_out_not_quiet(seeded_client: TestClient) -> None:
    assert "Closed Gorge camping area" not in names(seeded_client)


def test_a_campground_not_booked_in_the_last_year_of_history_is_left_out(
    seeded_client: TestClient,
) -> None:
    found = names(seeded_client)

    assert "Retired Ridge camping area" not in found
    assert "Lapsed Lagoon camping area" not in found  # March 2024; the history ends Dec 2025


def test_a_campground_with_too_little_history_is_left_out(seeded_client: TestClient) -> None:
    assert "Thin Creek camping area" not in names(seeded_client)


def test_a_result_names_the_openstreetmap_object_it_matched(seeded_client: TestClient) -> None:
    by_name = {c["name"]: c for c in results(seeded_client)}

    assert (by_name[QUIET]["osm_type"], by_name[QUIET]["osm_id"]) == ("way", 4242)
    assert (by_name[BUSY]["osm_type"], by_name[BUSY]["osm_id"]) == (None, None)  # no match


def test_park_narrows_the_search(seeded_client: TestClient) -> None:
    assert names(seeded_client, park="Busy Coast National Park") == [BUSY]


def test_limit_keeps_the_quietest(seeded_client: TestClient) -> None:
    assert names(seeded_client, limit=3) == names(seeded_client)[:3]


def test_q_matches_part_of_a_campground_name_in_any_case(seeded_client: TestClient) -> None:
    assert names(seeded_client, q="CREEK") == [QUIET, MIDDLE]  # still quietest first


def test_q_matches_the_park_name_too(seeded_client: TestClient) -> None:
    assert names(seeded_client, q="busy coast") == [BUSY]


def test_q_with_no_match_finds_nothing(seeded_client: TestClient) -> None:
    assert names(seeded_client, q="nowhere") == []


def test_q_and_park_must_both_match(seeded_client: TestClient) -> None:
    assert names(seeded_client, q="creek", park="Busy Coast National Park") == []


def test_a_page_with_everything_has_no_next(seeded_client: TestClient) -> None:
    assert page(seeded_client)["next"] is None


def test_next_continues_where_the_page_ended(seeded_client: TestClient) -> None:
    first = page(seeded_client, limit=3)
    rest = page(seeded_client, limit=3, after=first["next"])

    assert first["next"] is not None
    assert [c["name"] for c in rest["results"]] == [MIDDLE, BUSY]
    assert rest["next"] is None


def test_one_at_a_time_gives_the_same_order_through_a_tie(seeded_client: TestClient) -> None:
    """Paging on busyness alone would skip or repeat TWIN after QUIET: both are 0."""
    paged: list[str] = []
    after = None
    while True:
        one = page(seeded_client, limit=1, **({} if after is None else {"after": after}))
        paged += [c["name"] for c in one["results"]]
        after = one["next"]
        if after is None:
            break

    assert paged == names(seeded_client)


def test_next_pages_keep_the_filters_sent_again(seeded_client: TestClient) -> None:
    first = page(seeded_client, q="creek", limit=1)
    second = page(seeded_client, q="creek", limit=1, after=first["next"])

    assert [c["name"] for c in first["results"] + second["results"]] == [QUIET, MIDDLE]
    assert second["next"] is None


def map_names(client: TestClient, **params: Any) -> list[str]:
    response = client.get("/campgrounds/quiet/map", params={**SATURDAY, **params})
    assert response.status_code == 200
    return [c["name"] for c in response.json()["results"]]


def test_the_map_has_every_result_in_rank_order_on_one_page(seeded_client: TestClient) -> None:
    assert page(seeded_client, limit=2)["next"] is not None  # more than one page of the search
    assert map_names(seeded_client) == names(seeded_client)


def test_the_map_takes_the_search_filters(seeded_client: TestClient) -> None:
    assert map_names(seeded_client, q="creek") == [QUIET, MIDDLE]
    assert map_names(seeded_client, park="Busy Coast National Park") == [BUSY]


@pytest.mark.parametrize("wildcard", ["%%", "__"])
def test_q_wildcards_are_plain_characters(seeded_client: TestClient, wildcard: str) -> None:
    """In LIKE, % is any text and _ any one character: unescaped, these would match everything."""
    assert names(seeded_client, q=wildcard) == []


NEAR = {"near_lat": -28.0, "near_lon": 152.5}


def test_near_a_place_keeps_located_campgrounds_within_the_km(seeded_client: TestClient) -> None:
    found = results(seeded_client, **NEAR, within_km=40)

    # Twin Hollow ~10 km, Big Hollow ~33 km; Middle Creek is 49 km and Quiet Creek unlocated.
    assert [c["name"] for c in found] == [BIG, TWIN]  # still quietest, then biggest, first


def test_each_result_near_a_place_says_how_far(seeded_client: TestClient) -> None:
    found = results(seeded_client, **NEAR, within_km=200)

    assert len(found) == 4  # every located campground; Busy Beach is the farthest, ~188 km
    for c in found:
        assert c["distance_km"] == pytest.approx(km((-28.0, 152.5), (c["lat"], c["lon"])))


def test_without_a_place_there_is_no_distance(seeded_client: TestClient) -> None:
    assert {c["distance_km"] for c in results(seeded_client)} == {None}


YEAR = "/campgrounds/quiet/year"


def year_view(client: TestClient, **params: Any) -> dict[str, Any]:
    response = client.get(YEAR, params={"year": 2027, **params})
    assert response.status_code == 200
    return response.json()


def test_the_year_view_agrees_with_the_search_night_by_night(seeded_client: TestClient) -> None:
    body = year_view(seeded_client)
    saturday = (date(2027, 3, 13) - date(2027, 1, 1)).days
    found = results(seeded_client)  # the same Saturday

    assert (body["first_night"], body["nights"]) == ("2027-01-01", 365)
    assert body["open"][saturday] == len(found)
    assert body["busyness"][saturday] == pytest.approx(
        sum(c["busyness"] for c in found) / len(found), abs=1e-5
    )


def test_a_night_they_are_all_usually_closed_is_none(seeded_client: TestClient) -> None:
    body = year_view(seeded_client)
    april = (date(2027, 4, 20) - date(2027, 1, 1)).days  # the seed books March only, mostly

    assert (body["busyness"][april], body["open"][april]) == (None, 0)


def test_the_year_view_names_its_holidays(seeded_client: TestClient) -> None:
    holidays = {(h["name"], h["night"], h["nights"]) for h in year_view(seeded_client)["holidays"]}

    easter = (date(2027, 3, 25) - date(2027, 1, 1)).days  # Thursday night to Sunday night
    assert ("easter", easter, 4) in holidays


def test_an_area_with_no_campgrounds_is_a_year_of_none(seeded_client: TestClient) -> None:
    body = year_view(seeded_client, near_lat=-16.9, near_lon=145.8, within_km=10)  # Cairns

    assert set(body["busyness"]) == {None}
    assert set(body["open"]) == {0}
