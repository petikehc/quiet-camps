"""GET /campgrounds/{campground_id}/years: booked sites by month, every year, for year-on-year.

The history ends with 2025 (conftest.seed_search_history). Middle Creek books 2 sites each
March 2022-2025. Early Bird (conftest.seed_lead_times) books December 2022 and 2024, and
October 2025: a 1-site and a 3-site booking on a Saturday, and a Tuesday in two files.
"""

from typing import Any

from fastapi.testclient import TestClient

MIDDLE = "Middle Creek camping area"
QUIET = "Quiet Creek camping area"
EARLY = "Early Bird camping area"
RETIRED = "Retired Ridge camping area"
PROBLEM = "application/problem+json"


def years(client: TestClient, campground_id: int) -> dict[str, Any]:
    response = client.get(f"/campgrounds/{campground_id}/years")
    assert response.status_code == 200
    return response.json()


def sites(body: dict[str, Any], year: int) -> list[int | None]:
    [found] = [y for y in body["years"] if y["year"] == year]
    assert [m["month"] for m in found["months"]] == list(range(1, 13))
    return [m["sites"] for m in found["months"]]


def test_every_year_from_the_first_booking_to_the_end_of_history(
    seeded_client: TestClient, seeded_ids: dict[str, int]
) -> None:
    body = years(seeded_client, seeded_ids[MIDDLE])

    assert body["campground_id"] == seeded_ids[MIDDLE]
    assert body["through"] == "2025-12-31"
    assert [y["year"] for y in body["years"]] == [2022, 2023, 2024, 2025]


def test_months_before_the_first_booking_are_null_and_empty_months_0(
    seeded_client: TestClient, seeded_ids: dict[str, int]
) -> None:
    body = years(seeded_client, seeded_ids[MIDDLE])

    assert sites(body, 2022) == [None, None, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    assert sites(body, 2025) == [0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0]


def test_the_latest_quarter_is_not_history_yet(
    seeded_client: TestClient, seeded_ids: dict[str, int]
) -> None:
    body = years(seeded_client, seeded_ids[QUIET])  # also booked 15 January 2026

    assert body["years"][-1]["year"] == 2025


def test_sites_are_counted_once_per_booking_and_summed(
    seeded_client: TestClient, seeded_ids: dict[str, int]
) -> None:
    body = years(seeded_client, seeded_ids[EARLY])

    assert sites(body, 2022)[11] == 1
    assert sites(body, 2024)[11] == 4
    assert sites(body, 2025)[9] == 5  # 1 + 3 on the Saturday, 1 on the Tuesday in two files


def test_a_retired_campground_runs_on_with_0s(
    seeded_client: TestClient, seeded_ids: dict[str, int]
) -> None:
    body = years(seeded_client, seeded_ids[RETIRED])  # booked in March 2012-2015

    assert body["years"][0]["year"] == 2012
    assert sites(body, 2015)[2] == 1
    assert sites(body, 2016) == [0] * 12
    assert body["years"][-1]["year"] == 2025


def test_an_unknown_campground_is_a_404_problem(seeded_client: TestClient) -> None:
    response = seeded_client.get("/campgrounds/999999/years")

    assert response.status_code == 404
    assert response.headers["content-type"] == PROBLEM
    assert "999999" in response.json()["detail"]  # not the router's own 404 for a missing route
