"""GET /campgrounds/{campground_id}/lead-time: how far ahead nights were booked.

Early Bird's bookings (conftest.seed_lead_times) are in days ahead: Christmas 2024 0, 10, 60
and 400; a Saturday 0 and 14 (that one with 3 sites); a Tuesday booked 3 days after the night,
in two files. The history ends with 2025, so the last 3 years are 2023-2025.
"""

from typing import Any

from fastapi.testclient import TestClient

EARLY = "Early Bird camping area"
MIDDLE = "Middle Creek camping area"
RETIRED = "Retired Ridge camping area"
PROBLEM = "application/problem+json"
WEEKS = [0, 1, 2, 4, 8, 13, 26, 52]


def lead_time(client: TestClient, campground_id: int) -> dict[str, Any]:
    response = client.get(f"/campgrounds/{campground_id}/lead-time")
    assert response.status_code == 200
    return response.json()


def shares(group: dict[str, Any]) -> list[float]:
    assert [b["weeks"] for b in group["booked_by"]] == WEEKS
    return [b["share"] for b in group["booked_by"]]


def by_name(body: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {g["group"]: g for g in body["groups"]}


def test_covers_the_last_3_years_of_history(
    seeded_client: TestClient, seeded_ids: dict[str, int]
) -> None:
    body = lead_time(seeded_client, seeded_ids[EARLY])

    assert body["campground_id"] == seeded_ids[EARLY]
    assert (body["since"], body["until"]) == ("2023-01-01", "2025-12-31")


def test_holidays_first_then_weekends_then_weeknights(
    seeded_client: TestClient, seeded_ids: dict[str, int]
) -> None:
    body = lead_time(seeded_client, seeded_ids[EARLY])

    # Christmas 2022 is before the window and January 2026 after it: neither counts.
    assert [(g["group"], g["nights"]) for g in body["groups"]] == [
        ("christmas", 4),
        ("weekend", 2),  # 3 sites in one booking are one booked night
        ("weeknight", 1),  # one booking in two files is one booked night
    ]


def test_shares_booked_by_each_number_of_weeks_ahead(
    seeded_client: TestClient, seeded_ids: dict[str, int]
) -> None:
    groups = by_name(lead_time(seeded_client, seeded_ids[EARLY]))

    #                                          0     1     2     4    8    13    26    52 weeks
    assert shares(groups["christmas"]) == [1.0, 0.75, 0.5, 0.5, 0.5, 0.25, 0.25, 0.25]
    assert shares(groups["weekend"]) == [1.0, 0.5, 0.5, 0, 0, 0, 0, 0]  # 14 days is 2 weeks


def test_booked_after_the_night_counts_as_the_same_day(
    seeded_client: TestClient, seeded_ids: dict[str, int]
) -> None:
    groups = by_name(lead_time(seeded_client, seeded_ids[EARLY]))

    assert shares(groups["weeknight"]) == [1.0, 0, 0, 0, 0, 0, 0, 0]


def test_only_the_groups_with_bookings(
    seeded_client: TestClient, seeded_ids: dict[str, int]
) -> None:
    body = lead_time(seeded_client, seeded_ids[MIDDLE])  # week-10 Saturdays, booked on the day

    assert [(g["group"], g["nights"]) for g in body["groups"]] == [("weekend", 3)]


def test_a_campground_without_recent_bookings_has_no_groups(
    seeded_client: TestClient, seeded_ids: dict[str, int]
) -> None:
    body = lead_time(seeded_client, seeded_ids[RETIRED])

    assert body["groups"] == []
    assert body["until"] == "2025-12-31"


def test_an_unknown_campground_is_a_404_problem(seeded_client: TestClient) -> None:
    response = seeded_client.get("/campgrounds/999999/lead-time")

    assert response.status_code == 404
    assert response.headers["content-type"] == PROBLEM
    assert "999999" in response.json()["detail"]
