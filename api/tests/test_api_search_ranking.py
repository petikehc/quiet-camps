"""The search over a small seeded history, built once per test session by `seeded_client`."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

SEARCH = "/campgrounds/quiet"
# The Saturday of ISO week 10 in 2027: compared with week-10 Saturdays in 2022-2025.
SATURDAY = {"arrive": "2027-03-13", "depart": "2027-03-14"}

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

    assert {c["name"] for c in found[:2]} == {QUIET, TWIN}
    assert found[0]["id"] < found[1]["id"]  # a tie goes to the lower id
    assert [c["name"] for c in found[2:]] == [MIDDLE, BUSY]


def test_busyness_is_against_each_campgrounds_own_busy_nights(seeded_client: TestClient) -> None:
    found = {c["name"]: c for c in results(seeded_client)}

    assert found[QUIET]["busyness"] == 0
    assert found[MIDDLE]["busyness"] == 2  # 2 sites; its busy night (p95) is under 1, so 1
    assert found[BUSY]["busyness"] == 10
    assert found[QUIET]["history"] == 4  # one week-10 Saturday a year, 2022-2025


def test_a_campground_closed_in_march_is_left_out_not_quiet(seeded_client: TestClient) -> None:
    assert "Closed Gorge camping area" not in names(seeded_client)


def test_a_campground_not_booked_since_2024_is_left_out(seeded_client: TestClient) -> None:
    assert "Retired Ridge camping area" not in names(seeded_client)


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
    assert [c["name"] for c in rest["results"]] == [BUSY]
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


@pytest.mark.parametrize("wildcard", ["%%", "__"])
def test_q_wildcards_are_plain_characters(seeded_client: TestClient, wildcard: str) -> None:
    """In LIKE, % is any text and _ any one character: unescaped, these would match everything."""
    assert names(seeded_client, q=wildcard) == []
