"""Every error as an RFC 9457 problem, so clients handle one shape whatever went wrong."""

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from quiet_camps.api.campground_service import CampgroundNotFound

PROBLEM = "application/problem+json"


def problem(
    status: int, detail: str, headers: Mapping[str, str] | None = None, **extra: Any
) -> JSONResponse:
    # type "about:blank": we have no page per problem, so the title is the HTTP phrase.
    body = {
        "type": "about:blank",
        "title": HTTPStatus(status).phrase,
        "status": status,
        "detail": detail,
        **extra,
    }
    return JSONResponse(body, status, headers=headers, media_type=PROBLEM)


def field_error(error: Mapping[str, Any]) -> dict[str, str | None]:
    """One pydantic error as {field, message}; a rule across fields has no field."""
    field = ".".join(str(part) for part in error["loc"][1:])  # loc[0] is "query", "body"…
    # Our own ValueError arrives as "Value error, <ours>"; the original is in ctx.
    message = str(error["ctx"]["error"]) if error["type"] == "value_error" else error["msg"]
    return {"field": field or None, "message": message}


async def invalid_request(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    errors = [field_error(e) for e in exc.errors()]
    noun = "error" if len(errors) == 1 else "errors"
    return problem(422, f"The request has {len(errors)} {noun}.", errors=errors)


async def http_error(request: Request, exc: Exception) -> JSONResponse:
    """404 and 405 from the router, and any HTTPException a route raises."""
    assert isinstance(exc, HTTPException)
    return problem(exc.status_code, str(exc.detail), exc.headers)  # keeps Allow on a 405


async def crash(request: Request, exc: Exception) -> JSONResponse:
    # Never echo the exception: it can hold secrets. Starlette still logs it with the traceback.
    return problem(500, "Something went wrong on our side.")


async def not_found(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, CampgroundNotFound)
    return problem(404, str(exc))


def add_problem_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, invalid_request)
    # Starlette's, not FastAPI's subclass: the router raises Starlette's for 404 and 405.
    app.add_exception_handler(HTTPException, http_error)
    app.add_exception_handler(Exception, crash)
    app.add_exception_handler(CampgroundNotFound, not_found)
