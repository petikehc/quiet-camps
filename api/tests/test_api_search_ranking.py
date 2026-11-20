"""The search over a small seeded history, built once per test session by `seeded_client`."""

from typing import Any

from fastapi.testclient import TestClient

SEARCH = "/campgrounds/quiet"
# The Saturday of ISO week 10 in 2027: compared with week-10 Saturdays in 2022-2025.
SATURDAY = {"arrive": "2027-03-13", "depart": "2027-03-14"}

QUIET = "Quiet Creek camping area"
MIDDLE = "Middle Creek camping area"
BUSY = "Busy Beach camping area"


def results(client: TestClient, **params: Any) -> list[dict[str, Any]]:
    response = client.get(SEARCH, params={**SATURDAY, **params})
    assert response.status_code == 200
    return response.json()["results"]


def names(client: TestClient, **params: Any) -> list[str]:
    return [c["name"] for c in results(client, **params)]


def test_quietest_comes_first(seeded_client: TestClient) -> None:
    assert names(seeded_client) == [QUIET, MIDDLE, BUSY]


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


def test_park_narrows_the_search(seeded_client: TestClient) -> None:
    assert names(seeded_client, park="Busy Coast National Park") == [BUSY]


def test_limit_keeps_the_quietest(seeded_client: TestClient) -> None:
    assert names(seeded_client, limit=2) == [QUIET, MIDDLE]
