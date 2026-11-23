from typing import Any

import pytest
from fastapi.testclient import TestClient

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
