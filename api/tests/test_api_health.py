from typing import Annotated

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from quiet_camps.api.app import create_app
from quiet_camps.api.db import get_session
from quiet_camps.api.settings import Settings

# Nothing listens on port 1, so connecting fails straight away.
UNREACHABLE = "postgresql+psycopg://quiet_camps:quiet_camps@localhost:1/quiet_camps"


def test_health_says_ok_when_the_database_answers(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_is_503_when_the_database_is_unreachable() -> None:
    with TestClient(create_app(Settings(database_url=UNREACHABLE))) as client:
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "unreachable"}


def test_health_only_answers_get(client: TestClient) -> None:
    response = client.post("/health")

    assert response.status_code == 405


def test_session_goes_back_to_the_pool_when_the_route_fails(api_settings: Settings) -> None:
    app = create_app(api_settings)

    @app.get("/fails")
    async def fails(session: Annotated[AsyncSession, Depends(get_session)]) -> None:
        await session.execute(text("SELECT 1"))
        raise RuntimeError("the route failed after using the database")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/fails")
        checked_out = app.state.engine.pool.checkedout()

    assert response.status_code == 500
    assert checked_out == 0
