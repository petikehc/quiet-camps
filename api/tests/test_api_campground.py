"""GET /campgrounds/{campground_id}: one campground, or a 404 problem."""

from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient

from quiet_camps.api.app import create_app
from quiet_camps.api.campground_service import CampgroundSource
from quiet_camps.api.campgrounds import get_source
from quiet_camps.api.settings import Settings
from quiet_camps.db.models import Campground

PROBLEM = "application/problem+json"
QUIET = "Quiet Creek camping area"
RETIRED = "Retired Ridge camping area"
RANGE = "Test Range National Park"


def test_a_campground_by_id(seeded_client: TestClient, seeded_ids: dict[str, int]) -> None:
    quiet = seeded_ids[QUIET]

    response = seeded_client.get(f"/campgrounds/{quiet}")

    assert response.status_code == 200
    # Exactly these keys: nothing internal (park_key, osm_id, match_score) leaks out.
    assert response.json() == {
        "id": quiet,
        "name": QUIET,
        "park_name": RANGE,
        "last_night": "2026-01-15",
        "active": True,
        "lat": None,  # the seed never runs `qc locations`
        "lon": None,
        "location_source": None,
        "location_flags": [],
    }


def test_a_retired_campground_is_found_but_not_active(
    seeded_client: TestClient, seeded_ids: dict[str, int]
) -> None:
    retired = seeded_ids[RETIRED]

    body = seeded_client.get(f"/campgrounds/{retired}").json()

    assert body["active"] is False
    assert body["last_night"] == "2015-03-03"


def test_an_unknown_id_is_a_404_problem(seeded_client: TestClient) -> None:
    response = seeded_client.get("/campgrounds/999999")

    assert response.status_code == 404
    assert response.headers["content-type"] == PROBLEM
    body = response.json()
    assert body["title"] == "Not Found"
    assert body["status"] == 404
    assert "999999" in body["detail"]


@pytest.mark.parametrize("bad_id", ["abc", "1.5", "0", "-3"])
def test_an_id_that_isnt_a_positive_whole_number_is_a_422_problem(
    seeded_client: TestClient, bad_id: str
) -> None:
    response = seeded_client.get(f"/campgrounds/{bad_id}")

    assert response.status_code == 422
    assert response.headers["content-type"] == PROBLEM
    assert [e["field"] for e in response.json()["errors"]] == ["campground_id"]


class OneCampground:
    """A source with a single campground, for the route without a database."""

    async def get(self, campground_id: int) -> Campground | None:
        if campground_id != 7:
            return None
        return Campground(
            id=7,
            name="Fake Flat camping area",
            park_name="Nowhere National Park",
            last_night=date(2025, 12, 30),
            lat=-27.5,
            lon=153.0,
            location_source="manual",
            location_flags=[],
        )

    async def history_end(self) -> date | None:
        return date(2025, 12, 31)


@pytest.fixture
def faked_client() -> Iterator[TestClient]:
    # A database that doesn't exist: any query would fail the test.
    app = create_app(Settings(database_url="postgresql+psycopg://nobody@localhost:1/nowhere"))

    def one_campground() -> CampgroundSource:
        return OneCampground()

    app.dependency_overrides[get_source] = one_campground
    with TestClient(app) as client:
        yield client


def test_the_route_reads_from_whatever_source_it_is_given(faked_client: TestClient) -> None:
    body = faked_client.get("/campgrounds/7").json()

    assert body["name"] == "Fake Flat camping area"
    assert body["active"] is True
    assert body["location_source"] == "manual"


def test_a_source_without_it_is_a_404(faked_client: TestClient) -> None:
    assert faked_client.get("/campgrounds/8").status_code == 404
