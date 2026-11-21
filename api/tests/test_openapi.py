"""The OpenAPI document: the contract web/src/api/schema.d.ts is generated from."""

import json
from collections.abc import Iterator
from typing import Any

import pytest

from quiet_camps.api.openapi import OPENAPI_FILE, openapi_document
from quiet_camps.api.problems import PROBLEM

REF = "#/components/schemas/"


def spec() -> dict[str, Any]:
    return json.loads(openapi_document())


def responses(document: dict[str, Any]) -> Iterator[tuple[str, int, dict[str, Any]]]:
    for path, operations in document["paths"].items():
        for operation in operations.values():
            for status, response in operation["responses"].items():
                yield path, int(status), response


def statuses(document: dict[str, Any], path: str) -> set[int]:
    return {int(s) for s in document["paths"][path]["get"]["responses"]}


def test_the_committed_document_is_up_to_date() -> None:
    assert OPENAPI_FILE.read_text() == openapi_document(), (
        "The API changed: run `uv run qc openapi`, then `pnpm api:types` in web/"
    )


def test_every_error_is_documented_as_a_problem() -> None:
    errors = [(path, status, r) for path, status, r in responses(spec()) if status >= 400]

    assert errors
    for path, status, response in errors:
        assert list(response["content"]) == [PROBLEM], (path, status)
        expected = "ValidationProblem" if status == 422 else "Problem"
        assert response["content"][PROBLEM]["schema"] == {"$ref": REF + expected}, (path, status)


def test_fastapis_own_validation_error_shape_is_gone() -> None:
    assert "HTTPValidationError" not in spec()["components"]["schemas"]


@pytest.mark.parametrize(
    ("path", "documented"),
    [
        ("/health", {200}),
        ("/campgrounds/quiet", {200, 422}),
        ("/campgrounds/{campground_id}", {200, 404, 422}),
        ("/campgrounds/{campground_id}/calendar", {200, 404, 422}),
        ("/year/{year}", {200, 304, 404, 422}),
    ],
)
def test_each_route_documents_the_statuses_it_returns(path: str, documented: set[int]) -> None:
    assert statuses(spec(), path) == documented


def test_the_year_is_documented_as_its_model() -> None:
    ok = spec()["paths"]["/year/{year}"]["get"]["responses"]["200"]

    assert ok["content"]["application/json"]["schema"] == {"$ref": REF + "YearOut"}


def test_experiments_never_reach_the_document(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPERIMENTS", "true")

    assert not [path for path in spec()["paths"] if path.startswith("/experiment")]
