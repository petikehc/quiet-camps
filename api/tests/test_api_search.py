from datetime import date
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.rows import TupleRow

from quiet_camps.db.derived import refresh_derived
from quiet_camps.db.load import ensure_areas

SEARCH = "/campgrounds/quiet"
MAP = "/campgrounds/quiet/map"
EASTER_2027 = {"arrive": "2027-03-26", "depart": "2027-03-29"}

RESULT_FIELDS = {
    "id",
    "name",
    "park_name",
    "busyness",
    "typical_sites",
    "history",
    "busy_night_sites",
    "lat",
    "lon",
    "location_source",
    "location_flags",
    "osm_type",
    "osm_id",
    "qpws_url",
    "qpws_url_kind",
    "distance_km",
}


def test_search_answers_with_a_list_of_results(client: TestClient) -> None:
    response = client.get(SEARCH, params=EASTER_2027)

    assert response.status_code == 200
    assert response.json() == {"results": [], "next": None}  # the test database is empty


def test_park_and_limit_are_accepted(client: TestClient) -> None:
    response = client.get(
        SEARCH, params={**EASTER_2027, "park": "Sundown National Park", "limit": 5}
    )

    assert response.status_code == 200


def test_sixty_nights_is_allowed(client: TestClient) -> None:
    response = client.get(SEARCH, params={"arrive": "2027-01-01", "depart": "2027-03-02"})

    assert response.status_code == 200


BAD_FILTERS = [
    ({"depart": "2027-03-29"}, "arrive is missing"),
    ({"arrive": "2027-03-26"}, "depart is missing"),
    ({"arrive": "26/03/2027", "depart": "2027-03-29"}, "arrive isn't an ISO date"),
    ({"arrive": "2027-03-29", "depart": "2027-03-29"}, "no nights"),
    ({"arrive": "2027-03-29", "depart": "2027-03-26"}, "depart before arrive"),
    ({"arrive": "2027-01-01", "depart": "2027-03-03"}, "61 nights"),
    ({**EASTER_2027, "q": "a"}, "q shorter than 2"),
    ({**EASTER_2027, "q": "a" * 101}, "q longer than 100"),
    ({**EASTER_2027, "near_lat": -26.4, "near_lon": 153.1}, "near without within_km"),
    ({**EASTER_2027, "near_lat": -26.4, "within_km": 50}, "near without its lon"),
    ({**EASTER_2027, "near_lat": -26.4, "near_lon": 153.1, "within_km": 5}, "within 5 km"),
    ({**EASTER_2027, "near_lat": 51.5, "near_lon": 153.1, "within_km": 50}, "near London"),
]
BAD_PAGING = [
    ({**EASTER_2027, "limit": 0}, "limit below 1"),
    ({**EASTER_2027, "limit": 101}, "limit above 100"),
    ({**EASTER_2027, "after": "not-a-cursor"}, "after isn't base64 JSON"),
    ({**EASTER_2027, "after": "WzFd"}, "after is [1], not [busyness, peak, id]"),
]


@pytest.mark.parametrize(("params", "why"), BAD_FILTERS + BAD_PAGING)
def test_bad_searches_are_422(client: TestClient, params: dict[str, Any], why: str) -> None:
    response = client.get(SEARCH, params=params)

    assert response.status_code == 422, why


@pytest.mark.parametrize("path", [SEARCH, MAP])
def test_each_result_has_the_documented_fields(client: TestClient, path: str) -> None:
    """The test database is empty, so check the response model through the OpenAPI schema."""
    schema = client.get("/openapi.json").json()
    ok = schema["paths"][path]["get"]["responses"]["200"]["content"]["application/json"]

    page = _resolve(schema, ok["schema"])
    result = _resolve(schema, page["properties"]["results"]["items"])

    assert set(result["properties"]) == RESULT_FIELDS


def test_the_map_answers_with_every_result_and_no_paging(client: TestClient) -> None:
    response = client.get(MAP, params=EASTER_2027)

    assert response.status_code == 200
    assert response.json() == {"results": []}  # no `next`: the test database is empty


@pytest.mark.parametrize(("params", "why"), BAD_FILTERS)
def test_the_map_rejects_the_same_bad_filters(
    client: TestClient, params: dict[str, Any], why: str
) -> None:
    response = client.get(MAP, params=params)

    assert response.status_code == 422, why


def _resolve(schema: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    """Follow a {"$ref": "#/components/schemas/Name"} to the schema it names."""
    if "$ref" not in node:
        return node
    name = node["$ref"].rsplit("/", 1)[-1]
    return schema["components"]["schemas"][name]


@pytest.mark.parametrize("year", [2010, 2100, "x"])
def test_a_year_outside_the_calendar_is_422(client: TestClient, year: int | str) -> None:
    assert client.get("/campgrounds/quiet/year", params={"year": year}).status_code == 422


def book(conn: psycopg.Connection[TupleRow], area: str, night: date) -> None:
    area_id = ensure_areas(conn, [("Range NP", area)])[("Range NP", area)]
    conn.execute(
        "INSERT INTO camp_night (area_id, night, booked_on, adults, state, source_file)"
        " VALUES (%s, %s, %s, 2, 'QLD', 'q.csv')",
        (area_id, night, night),
    )


def test_a_night_whose_kind_is_rare_falls_back_to_its_fortnight(
    conn: psycopg.Connection[TupleRow], client: TestClient
) -> None:
    """23 Dec 2026 is the Wednesday of week 52, which is inside Christmas most years: too few
    past nights of its own. The Wednesdays of weeks 51-52 together have five years."""
    for year in range(2021, 2026):
        book(conn, "Edge camping area", date(year, 12, 10))  # open each December
    book(conn, "Edge camping area", date(2026, 1, 15))  # makes 2025 history
    list(refresh_derived(conn))
    conn.commit()

    response = client.get(SEARCH, params={"arrive": "2026-12-23", "depart": "2026-12-24"})

    assert [c["name"] for c in response.json()["results"]] == ["Edge camping area"]
