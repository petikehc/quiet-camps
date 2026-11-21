"""Every error is an RFC 9457 problem: one shape for clients, whatever went wrong."""

from typing import Any

import httpx2 as httpx
from fastapi.testclient import TestClient

from quiet_camps.api.app import create_app
from quiet_camps.api.problems import Problem, ValidationProblem
from quiet_camps.api.settings import Settings

PROBLEM = "application/problem+json"
SEARCH = "/campgrounds/quiet"
EASTER_2027 = {"arrive": "2027-03-26", "depart": "2027-03-29"}


def problem(response: httpx.Response, status: int, title: str) -> dict[str, Any]:
    """Check the parts every problem has, and return the body for the rest."""
    assert response.status_code == status
    assert response.headers["content-type"] == PROBLEM
    body = response.json()
    assert body["type"] == "about:blank"  # no problem page of our own: title is the HTTP phrase
    assert body["title"] == title
    assert body["status"] == status
    assert isinstance(body["detail"], str)
    return body


def test_each_invalid_field_is_one_error(client: TestClient) -> None:
    response = client.get(SEARCH, params={**EASTER_2027, "limit": 0, "q": "a"})

    body = problem(response, 422, "Unprocessable Content")
    assert {e["field"] for e in body["errors"]} == {"limit", "q"}
    assert all(e["message"] for e in body["errors"])


def test_a_missing_field_names_it(client: TestClient) -> None:
    response = client.get(SEARCH, params={"depart": "2027-03-29"})

    body = problem(response, 422, "Unprocessable Content")
    assert body["errors"] == [{"field": "arrive", "message": "Field required"}]


def test_a_rule_across_fields_has_no_field_and_our_own_message(client: TestClient) -> None:
    response = client.get(SEARCH, params={"arrive": "2027-03-29", "depart": "2027-03-26"})

    body = problem(response, 422, "Unprocessable Content")
    # Pydantic's msg is "Value error, depart must be after arrive": clients get ours alone.
    assert body["errors"] == [{"field": None, "message": "depart must be after arrive"}]


def test_an_unknown_path_is_a_404_problem(client: TestClient) -> None:
    problem(client.get("/nowhere"), 404, "Not Found")


def test_a_wrong_method_is_a_405_problem_that_keeps_allow(client: TestClient) -> None:
    response = client.post(SEARCH)

    problem(response, 405, "Method Not Allowed")
    assert response.headers["allow"] == "GET"


def test_a_crash_is_a_500_problem_that_hides_the_exception(api_settings: Settings) -> None:
    app = create_app(api_settings)

    @app.get("/crash")
    async def crash() -> None:
        raise RuntimeError("password=hunter2")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/crash")

    problem(response, 500, "Internal Server Error")
    assert "hunter2" not in response.text


def test_the_documented_models_describe_the_real_bodies(seeded_client: TestClient) -> None:
    # extra="forbid" on the models: a key the docs don't mention fails here.
    invalid = seeded_client.get(SEARCH, params={**EASTER_2027, "limit": 0, "q": "a"}).json()
    not_found = seeded_client.get("/campgrounds/999999").json()
    no_route = seeded_client.get("/nowhere").json()

    ValidationProblem.model_validate(invalid)
    Problem.model_validate(not_found)
    Problem.model_validate(no_route)
