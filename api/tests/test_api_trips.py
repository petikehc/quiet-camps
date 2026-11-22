"""GET /trips/{year}: a year of trips, home postcode to campground, for the homepage."""

from datetime import date
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.rows import TupleRow

from quiet_camps.db.campgrounds import assign_campgrounds
from quiet_camps.db.load import ensure_areas

type Conn = psycopg.Connection[TupleRow]

PARK = "Great Sandy National Park"
TEEWAH = "Teewah Beach camping zone 1"
UNLOCATED = "Somewhere camping area"


def book(conn: Conn, area: str, night: date, postcode: str | None, state: str = "QLD") -> None:
    area_id = ensure_areas(conn, [(PARK, area)])[(PARK, area)]
    conn.execute(
        "INSERT INTO camp_night (area_id, night, booked_on, adults, children, infants,"
        " postcode, state, source_file) VALUES (%s, %s, '2024-06-01', 2, 0, 0, %s, %s, 'q.csv')",
        (area_id, night, postcode, state),
    )


@pytest.fixture
def trips_client(conn: Conn, client: TestClient) -> TestClient:
    """2025 is history: two trips drawn, four left out."""
    book(conn, TEEWAH, date(2025, 4, 18), "4000")
    book(conn, TEEWAH, date(2025, 4, 19), "4000")  # the same stay's second night
    book(conn, TEEWAH, date(2025, 12, 31), "4810")
    book(conn, TEEWAH, date(2025, 5, 1), "4001")  # no centre
    book(conn, TEEWAH, date(2025, 5, 1), None)
    book(conn, TEEWAH, date(2025, 5, 1), "8001", state="OVERSEAS")
    book(conn, UNLOCATED, date(2025, 5, 1), "4000")
    book(conn, TEEWAH, date(2026, 1, 15), "4000")  # makes all of 2025 history
    assign_campgrounds(conn)
    conn.execute("UPDATE campground SET lat = -26.2, lon = 153.1 WHERE name = %s", (TEEWAH,))
    conn.execute(
        "INSERT INTO postcode_centroid VALUES ('4000', -27.47, 153.02), ('4810', -19.26, 146.82)"
    )
    conn.commit()
    return client


def trips(client: TestClient, year: int) -> dict[str, Any]:
    response = client.get(f"/trips/{year}")
    assert response.status_code == 200
    return response.json()


def test_trips_are_columns_from_postcode_to_campground(trips_client: TestClient) -> None:
    body = trips(trips_client, 2025)

    assert (body["year"], body["first_night"], body["nights"]) == (2025, "2025-01-01", 365)
    assert [o["postcode"] for o in body["origins"]] == ["4000", "4810"]
    assert body["origins"][0] == {"postcode": "4000", "lat": -27.47, "lon": 153.02}
    assert body["campgrounds"] == [{"id": body["campgrounds"][0]["id"], "name": TEEWAH,
                                    "lat": -26.2, "lon": 153.1}]  # fmt: skip
    easter = (date(2025, 4, 18) - date(2025, 1, 1)).days
    assert len(body["per_night"]) == 365
    assert (body["per_night"][easter], body["per_night"][364], sum(body["per_night"])) == (1, 1, 2)
    assert (body["origin"], body["campground"], body["sites"]) == ([0, 1], [0, 0], [1, 1])


def test_trips_without_a_line_are_counted(trips_client: TestClient) -> None:
    left_out = trips(trips_client, 2025)["left_out"]

    assert left_out == {"overseas": 1, "no_postcode": 1, "no_centroid": 1, "unlocated": 1}


def test_cached_for_a_day_with_a_weak_etag(trips_client: TestClient) -> None:
    response = trips_client.get("/trips/2025")
    etag = response.headers["etag"]

    assert response.headers["cache-control"] == "public, max-age=86400"
    assert etag.startswith('W/"')
    assert trips_client.get("/trips/2025", headers={"If-None-Match": etag}).status_code == 304


def test_a_year_without_history_is_a_404(trips_client: TestClient) -> None:
    response = trips_client.get("/trips/2026")

    assert response.status_code == 404
    assert "2026" in response.json()["detail"]


@pytest.mark.parametrize("number", ["2010", "x"])
def test_a_year_before_the_data_is_a_422(trips_client: TestClient, number: str) -> None:
    response = trips_client.get(f"/trips/{number}")

    assert response.status_code == 422
    assert [e["field"] for e in response.json()["errors"]] == ["year"]
