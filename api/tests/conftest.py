from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from psycopg.rows import TupleRow
from sqlalchemy import Engine, create_engine, make_url, text
from sqlalchemy.exc import OperationalError

from quiet_camps.api.app import create_app
from quiet_camps.api.settings import Settings
from quiet_camps.db.config import database_url, psycopg_conninfo

ALEMBIC_INI = Path(__file__).parents[1] / "alembic.ini"
TEST_DB = "quiet_camps_test"


@pytest.fixture
def test_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    """A fresh, empty database for each test, so tests never touch your loaded data."""
    url = make_url(database_url())
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)"))
            conn.execute(text(f"CREATE DATABASE {TEST_DB}"))
    except OperationalError as e:
        pytest.fail(f"Postgres isn't reachable. Start it with `docker compose up -d --wait`.\n{e}")
    finally:
        admin.dispose()

    test_url = url.set(database=TEST_DB)
    # Everything asks database_url(), so this points Alembic and psycopg at the test database.
    monkeypatch.setenv("DATABASE_URL", test_url.render_as_string(hide_password=False))
    engine = create_engine(test_url)
    yield engine
    engine.dispose()


@pytest.fixture
def alembic_cfg() -> Config:
    return Config(ALEMBIC_INI)


@pytest.fixture
def conn(test_db: Engine, alembic_cfg: Config) -> Iterator[psycopg.Connection[TupleRow]]:
    """A psycopg connection to a test database migrated to head."""
    command.upgrade(alembic_cfg, "head")
    with psycopg.connect(psycopg_conninfo()) as connection:
        yield connection


@pytest.fixture
def api_settings(test_db: Engine) -> Settings:
    """Settings pointing the API at the empty test database."""
    return Settings(database_url=test_db.url.render_as_string(hide_password=False))


@pytest.fixture
def client(api_settings: Settings) -> Iterator[TestClient]:
    # `with` keeps one event loop for every request; pooled async connections belong to a loop.
    with TestClient(create_app(api_settings)) as client:
        yield client
