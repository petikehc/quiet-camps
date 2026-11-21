"""GET /campgrounds/{campground_id}/calendar?year=: every night of a year, typical and actual.

The seed (conftest.seed_search_history) books Middle Creek 2 sites on the Saturday of ISO week
10 in 2022-2025, and nothing else, so March is its only open month. The history ends with
2025: the seed's last night is in January 2026, and the latest quarter isn't history yet.
"""

from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient

from quiet_camps.db.derived import YEARS_AHEAD

MIDDLE = "Middle Creek camping area"
QUIET = "Quiet Creek camping area"
THIN = "Thin Creek camping area"  # 2 years of history: below MIN_HISTORY
PROBLEM = "application/problem+json"


def calendar(client: TestClient, campground_id: int, year: int) -> dict[str, Any]:
    response = client.get(f"/campgrounds/{campground_id}/calendar", params={"year": year})
    assert response.status_code == 200
    return response.json()


def night(body: dict[str, Any], day: date) -> dict[str, Any]:
    return next(n for n in body["nights"] if n["night"] == day.isoformat())


@pytest.mark.parametrize(("year", "nights"), [(2024, 366), (2025, 365)])
def test_every_night_of_the_year_in_order(
    seeded_client: TestClient, seeded_ids: dict[str, int], year: int, nights: int
) -> None:
    body = calendar(seeded_client, seeded_ids[MIDDLE], year)

    assert body["campground_id"] == seeded_ids[MIDDLE]
    assert body["year"] == year
    days = [n["night"] for n in body["nights"]]
    assert len(days) == nights
    assert days[0] == f"{year}-01-01"
    assert days == sorted(days)


def test_a_past_night_has_typical_and_actual(
    seeded_client: TestClient, seeded_ids: dict[str, int]
) -> None:
    body = calendar(seeded_client, seeded_ids[MIDDLE], 2025)

    saturday = date.fromisocalendar(2025, 10, 6)
    assert night(body, saturday) == {
        "night": "2025-03-08",
        "kind": "week 10 6",
        "holiday": None,
        "typical_sites": 2.0,
        "busyness": 2.0,  # its 95th-percentile night is empty, so peak is the floor of 1 site
        "sites": 2,
    }
    tuesday = night(body, date.fromisocalendar(2025, 10, 2))
    assert (tuesday["typical_sites"], tuesday["sites"]) == (0.0, 0)  # open, nobody booked


def test_a_usually_closed_night_has_no_typical_but_its_actual_is_0(
    seeded_client: TestClient, seeded_ids: dict[str, int]
) -> None:
    april = night(calendar(seeded_client, seeded_ids[MIDDLE], 2025), date(2025, 4, 15))

    assert april["typical_sites"] is None
    assert april["busyness"] is None
    assert april["sites"] == 0


def test_a_future_night_has_typical_but_no_actual(
    seeded_client: TestClient, seeded_ids: dict[str, int]
) -> None:
    saturday = night(
        calendar(seeded_client, seeded_ids[MIDDLE], 2027), date.fromisocalendar(2027, 10, 6)
    )

    assert saturday["typical_sites"] == 2.0
    assert saturday["sites"] is None


def test_the_latest_quarter_has_no_actual_yet(
    seeded_client: TestClient, seeded_ids: dict[str, int]
) -> None:
    body = calendar(seeded_client, seeded_ids[QUIET], 2026)

    assert night(body, date(2026, 1, 15))["sites"] is None  # booked, but the quarter isn't over
    assert night(calendar(seeded_client, seeded_ids[QUIET], 2025), date(2025, 12, 31))["sites"] == 0


def test_too_little_history_has_no_typical(
    seeded_client: TestClient, seeded_ids: dict[str, int]
) -> None:
    body = calendar(seeded_client, seeded_ids[THIN], 2025)

    assert all(n["typical_sites"] is None for n in body["nights"])
    assert night(body, date.fromisocalendar(2025, 10, 2))["sites"] == 1


def test_holidays_are_named(seeded_client: TestClient, seeded_ids: dict[str, int]) -> None:
    good_friday = night(calendar(seeded_client, seeded_ids[MIDDLE], 2027), date(2027, 3, 26))

    assert (good_friday["kind"], good_friday["holiday"]) == ("easter +0", "easter")


def test_an_unknown_campground_is_a_404_problem(seeded_client: TestClient) -> None:
    response = seeded_client.get("/campgrounds/999999/calendar", params={"year": 2025})

    assert response.status_code == 404
    assert response.headers["content-type"] == PROBLEM
    assert "999999" in response.json()["detail"]


@pytest.mark.parametrize(
    "params", [{}, {"year": 2010}, {"year": date.today().year + YEARS_AHEAD + 1}, {"year": "x"}]
)
def test_a_year_outside_the_calendar_is_a_422_problem(
    seeded_client: TestClient, seeded_ids: dict[str, int], params: dict[str, Any]
) -> None:
    response = seeded_client.get(f"/campgrounds/{seeded_ids[MIDDLE]}/calendar", params=params)

    assert response.status_code == 422
    assert response.headers["content-type"] == PROBLEM
    assert [e["field"] for e in response.json()["errors"]] == ["year"]


def test_the_last_year_in_the_calendar_is_allowed(
    seeded_client: TestClient, seeded_ids: dict[str, int]
) -> None:
    last = date.today().year + YEARS_AHEAD

    assert len(calendar(seeded_client, seeded_ids[MIDDLE], last)["nights"]) >= 365
