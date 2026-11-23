"""GET /places: the ABS places plus our parks and campgrounds, best match first."""

from datetime import date

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.rows import TupleRow

from quiet_camps.db.campgrounds import assign_campgrounds
from quiet_camps.db.load import ensure_areas

type Conn = psycopg.Connection[TupleRow]

PARK = "Great Sandy National Park"


def book(conn: Conn, area: str, night: date) -> None:
    area_id = ensure_areas(conn, [(PARK, area)])[(PARK, area)]
    conn.execute(
        "INSERT INTO camp_night (area_id, night, booked_on, adults, state, source_file)"
        " VALUES (%s, %s, %s, 2, 'QLD', 'q.csv')",
        (area_id, night, night),
    )


@pytest.fixture
def places_client(conn: Conn, client: TestClient) -> TestClient:
    conn.execute(
        "INSERT INTO place (name, kind, lat, lon) VALUES"
        " ('Noosa', 'council', -26.39, 152.98), ('Noosa Heads', 'locality', -26.40, 153.09)"
    )
    book(conn, "Noosa River camping area", date(2025, 6, 1))
    book(conn, "Old Noosa Ridge camping area", date(2019, 6, 1))  # long retired
    assign_campgrounds(conn)
    conn.execute("UPDATE campground SET lat = -26.2, lon = 153.0")
    conn.commit()
    return client


def test_places_by_name_best_first(places_client: TestClient) -> None:
    response = places_client.get("/places", params={"q": "noosa"})

    assert response.status_code == 200
    found = [(p["name"], p["kind"]) for p in response.json()["results"]]
    assert found[0] == ("Noosa", "council")
    assert ("Noosa River camping area", "campground") in found
    assert (PARK, "park") not in found  # "noosa" isn't in its name


def test_a_retired_campground_is_no_place(places_client: TestClient) -> None:
    found = places_client.get("/places", params={"q": "old noosa ridge"}).json()["results"]

    assert "Old Noosa Ridge camping area" not in [p["name"] for p in found]


def test_a_one_letter_search_is_422(client: TestClient) -> None:
    assert client.get("/places", params={"q": "n"}).status_code == 422
