"""GET /year/{year}: campers per campground per night, for the 3D time-lapse.

The seed's history ends with 2025 (conftest). Every seeded booking is 2 adults per site.
"""

from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

MIDDLE = "Middle Creek camping area"
BUSY = "Busy Beach camping area"
EARLY = "Early Bird camping area"
RETIRED = "Retired Ridge camping area"
PROBLEM = "application/problem+json"


def year(client: TestClient, number: int) -> dict[str, Any]:
    response = client.get(f"/year/{number}")
    assert response.status_code == 200
    return response.json()


def campers(body: dict[str, Any], campground_id: int, night: date) -> int:
    row = [c["id"] for c in body["campgrounds"]].index(campground_id)
    column = (night - date.fromisoformat(body["first_night"])).days
    return body["values"][row * body["nights"] + column]


def test_every_night_of_a_past_year(seeded_client: TestClient) -> None:
    body = year(seeded_client, 2024)

    assert (body["year"], body["first_night"], body["nights"]) == (2024, "2024-01-01", 366)


def test_the_campgrounds_booked_that_year_in_id_order(
    seeded_client: TestClient, seeded_ids: dict[str, int]
) -> None:
    body = year(seeded_client, 2025)

    ids = [c["id"] for c in body["campgrounds"]]
    assert ids == sorted(ids)
    assert seeded_ids[RETIRED] not in ids  # last booked in 2015
    assert {MIDDLE, BUSY, EARLY} <= {c["name"] for c in body["campgrounds"]}
    assert set(body["campgrounds"][0]) == {"id", "name", "lat", "lon"}
    assert len(body["values"]) == len(ids) * body["nights"]


def test_values_are_campers_by_campground_then_night(
    seeded_client: TestClient, seeded_ids: dict[str, int]
) -> None:
    body = year(seeded_client, 2025)
    saturday = date.fromisocalendar(2025, 10, 6)

    assert campers(body, seeded_ids[MIDDLE], saturday) == 4  # 2 sites
    assert campers(body, seeded_ids[BUSY], saturday) == 20  # 10 sites
    assert campers(body, seeded_ids[MIDDLE], saturday.replace(day=9)) == 0
    # A 1-site and a 3-site booking; a Tuesday booking in two files counts once.
    assert campers(body, seeded_ids[EARLY], date(2025, 10, 11)) == 8
    assert campers(body, seeded_ids[EARLY], date(2025, 10, 14)) == 2


@pytest.mark.parametrize("number", [2026, 2029])
def test_a_year_without_history_is_a_404_problem(seeded_client: TestClient, number: int) -> None:
    response = seeded_client.get(f"/year/{number}")

    assert response.status_code == 404
    assert response.headers["content-type"] == PROBLEM
    assert str(number) in response.json()["detail"]
    assert "cache-control" not in response.headers


@pytest.mark.parametrize("number", ["2010", "x", "99999"])  # 99999: date() would fail
def test_a_year_before_the_data_is_a_422_problem(seeded_client: TestClient, number: str) -> None:
    response = seeded_client.get(f"/year/{number}")

    assert response.status_code == 422
    assert [e["field"] for e in response.json()["errors"]] == ["year"]


def test_cached_for_a_day_with_a_weak_etag(seeded_client: TestClient) -> None:
    response = seeded_client.get("/year/2025")

    assert response.headers["cache-control"] == "public, max-age=86400"
    assert response.headers["etag"].startswith('W/"')
    assert seeded_client.get("/year/2025").headers["etag"] == response.headers["etag"]
    assert seeded_client.get("/year/2024").headers["etag"] != response.headers["etag"]


def test_an_unchanged_year_is_a_304_without_a_body(seeded_client: TestClient) -> None:
    etag = seeded_client.get("/year/2025").headers["etag"]

    response = seeded_client.get("/year/2025", headers={"If-None-Match": etag})

    assert response.status_code == 304
    assert response.content == b""
    assert response.headers["etag"] == etag
    assert response.headers["cache-control"] == "public, max-age=86400"


def test_a_stale_etag_gets_the_whole_year(seeded_client: TestClient) -> None:
    response = seeded_client.get("/year/2025", headers={"If-None-Match": 'W/"stale", W/"old"'})

    assert response.status_code == 200
    assert response.json()["year"] == 2025


def test_big_responses_are_gzipped_small_ones_not(seeded_client: TestClient) -> None:
    big = seeded_client.get("/year/2025", headers={"Accept-Encoding": "gzip"})
    small = seeded_client.get("/health", headers={"Accept-Encoding": "gzip"})

    assert big.headers["content-encoding"] == "gzip"
    assert "content-encoding" not in small.headers


def test_holidays_are_spans_of_nights(seeded_client: TestClient) -> None:
    body = year(seeded_client, 2025)

    first = date.fromisoformat(body["first_night"])
    spans = {(h["name"], first + timedelta(days=h["night"]), h["nights"]) for h in body["holidays"]}
    assert ("easter", date(2025, 4, 17), 4) in spans  # Thursday night to Sunday night
    assert [h["name"] for h in body["holidays"]].count("christmas") == 2  # both ends of the year
    assert set(body["holidays"][0]) == {"name", "night", "nights"}
