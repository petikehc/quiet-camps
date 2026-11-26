"""POST /ask through the API, with a fake reader: no AWS."""

from collections.abc import Iterator
from datetime import date
from typing import cast

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg.rows import TupleRow

from quiet_camps.api.app import create_app
from quiet_camps.api.ask import AskState, get_today
from quiet_camps.api.ask_service import Holiday, ReaderUnavailable, Reading
from quiet_camps.api.settings import Settings

TODAY = date(2026, 11, 23)
NEAR_THE_SUNNY_COAST = Reading(
    arrive=date(2026, 11, 27),
    depart=date(2026, 11, 29),
    place="Sunny Coast",
    place_role="near",
    within_km=None,
)


class FakeReader:
    def __init__(self, reading: Reading | None = NEAR_THE_SUNNY_COAST) -> None:
        self.reading = reading
        self.reads = 0

    async def read(self, text: str, today: date, holidays: list[Holiday]) -> Reading:
        self.reads += 1
        if self.reading is None:
            raise ReaderUnavailable("down")
        return self.reading


@pytest.fixture
def reader() -> FakeReader:
    return FakeReader()


@pytest.fixture
def asking(
    api_settings: Settings,
    alembic_cfg: Config,
    conn: psycopg.Connection[TupleRow],
    reader: FakeReader,
) -> Iterator[TestClient]:
    """The API with asking switched on and the fake reader in place of Bedrock."""
    command.upgrade(alembic_cfg, "head")
    conn.execute(
        "INSERT INTO place (name, kind, lat, lon)"
        " VALUES ('Sunshine Coast', 'council', -26.65, 152.96)"
    )
    conn.commit()
    app = create_app(api_settings.model_copy(update={"ask_enabled": True}))
    ask_state: AskState = app.state.ask
    ask_state.reader = reader
    app.dependency_overrides[get_today] = lambda: TODAY
    with TestClient(app) as client:
        yield client


def ask(client: TestClient, text: str) -> dict[str, object]:
    response = client.post("/ask", json={"text": text})
    assert response.status_code == 200, response.text
    return response.json()


def test_plain_words_become_dates_and_a_place(asking: TestClient) -> None:
    assert ask(asking, "next weekend around the sunny coast") == {
        "arrive": "2026-11-27",
        "depart": "2026-11-29",
        "place": {"name": "Sunshine Coast", "kind": "council", "lat": -26.65, "lon": 152.96},
        "place_asked": None,
        "place_role": "near",
        "within_km": 50,
    }


def test_the_same_words_again_today_are_answered_without_asking(
    asking: TestClient, reader: FakeReader
) -> None:
    ask(asking, "next weekend around the sunny coast")
    ask(asking, "  Next weekend AROUND the sunny coast ")

    assert reader.reads == 1


def test_asking_too_often_is_429(asking: TestClient) -> None:
    ask_state: AskState = cast(FastAPI, asking.app).state.ask
    ask_state.limiter.limit = 2
    ask(asking, "this weekend near noosa")
    ask(asking, "easter near noosa")

    response = asking.post("/ask", json={"text": "christmas near noosa"})

    assert response.status_code == 429
    assert response.headers["retry-after"] == "3600"


def viewer_asks(client: TestClient, text: str, address: str) -> int:
    headers = {"CloudFront-Viewer-Address": address}
    return client.post("/ask", json={"text": text}, headers=headers).status_code


def test_behind_cloudfront_each_viewer_has_their_own_limit(asking: TestClient) -> None:
    # Behind CloudFront and the Lambda adapter, every request comes from one local address.
    app = cast(FastAPI, asking.app)
    app.state.settings = app.state.settings.model_copy(
        update={"client_ip_header": "cloudfront-viewer-address"}
    )
    ask_state: AskState = app.state.ask
    ask_state.limiter.limit = 2
    assert viewer_asks(asking, "this weekend near noosa", "203.0.113.9:1000") == 200
    assert viewer_asks(asking, "easter near noosa", "203.0.113.9:1001") == 200

    assert viewer_asks(asking, "christmas near noosa", "203.0.113.9:1002") == 429
    assert viewer_asks(asking, "christmas near noosa", "198.51.100.7:1000") == 200


@pytest.mark.parametrize("reader", [FakeReader(None)])
def test_a_reader_that_is_down_is_503(asking: TestClient) -> None:
    response = asking.post("/ask", json={"text": "next weekend"})

    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"


def test_too_many_words_are_422(asking: TestClient) -> None:
    assert asking.post("/ask", json={"text": "x" * 201}).status_code == 422


def test_switched_off_is_503_and_asks_nobody(client: TestClient) -> None:
    response = client.post("/ask", json={"text": "next weekend near noosa"})

    assert response.status_code == 503
    assert "switched off" in response.json()["detail"]
    ask_state: AskState = cast(FastAPI, client.app).state.ask
    assert ask_state.reader is None  # no AWS client was made
