from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from psycopg.rows import TupleRow
from sqlalchemy import URL, Engine, create_engine, make_url, select, text
from sqlalchemy.exc import OperationalError

from quiet_camps.api.app import create_app
from quiet_camps.api.settings import Settings
from quiet_camps.db.config import database_url, psycopg_conninfo
from quiet_camps.db.derived import refresh_derived
from quiet_camps.db.load import ensure_areas
from quiet_camps.db.models import Campground

type Conn = psycopg.Connection[TupleRow]

ALEMBIC_INI = Path(__file__).parents[1] / "alembic.ini"
TEST_DB = "quiet_camps_test"
SEARCH_DB = "quiet_camps_search_test"

RANGE = "Test Range National Park"
COAST = "Busy Coast National Park"
EARLY = "Early Bird camping area"


def fresh_database(name: str) -> URL:
    """Drop and recreate database `name` on the same server, and return its URL."""
    url = make_url(database_url())
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)"))
            conn.execute(text(f"CREATE DATABASE {name}"))
    except OperationalError as e:
        pytest.fail(f"Postgres isn't reachable. Start it with `docker compose up -d --wait`.\n{e}")
    finally:
        admin.dispose()
    return url.set(database=name)


@pytest.fixture
def test_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    """A fresh, empty database for each test, so tests never touch your loaded data."""
    test_url = fresh_database(TEST_DB)
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
def client(api_settings: Settings, alembic_cfg: Config) -> Iterator[TestClient]:
    """The API on the test database, migrated to head and empty."""
    command.upgrade(alembic_cfg, "head")
    # `with` keeps one event loop for every request; pooled async connections belong to a loop.
    with TestClient(create_app(api_settings)) as client:
        yield client


def book(
    conn: Conn,
    park: str,
    area: str,
    night: date,
    sites: int = 1,
    booked_on: date | None = None,  # the night itself unless given
    source_file: str = "test.csv",
) -> None:
    area_id = ensure_areas(conn, [(park, area)])[(park, area)]
    for _ in range(sites):  # identical rows in one file are separate sites
        conn.execute(
            "INSERT INTO camp_night (area_id, night, booked_on, adults, children, infants,"
            " state, source_file) VALUES (%s, %s, %s, 2, 0, 0, 'QLD', %s)",
            (area_id, night, booked_on or night, source_file),
        )


def seed_lead_times(conn: Conn) -> None:
    """Early Bird's bookings, where every lead-time answer is known: see test_api_lead_time.py.

    Only December and October, so it has no typical for March and stays out of the search.
    """
    christmas = date(2024, 12, 27)
    for days_ahead in (0, 10, 60, 400):
        book(conn, RANGE, EARLY, christmas, booked_on=christmas - timedelta(days=days_ahead))
    saturday = date(2025, 10, 11)
    book(conn, RANGE, EARLY, saturday)
    book(conn, RANGE, EARLY, saturday, sites=3, booked_on=saturday - timedelta(days=14))
    tuesday = date(2025, 10, 14)
    for source_file in ("test.csv", "overlap.csv"):  # one booking in two files
        book(
            conn,
            RANGE,
            EARLY,
            tuesday,
            booked_on=tuesday + timedelta(days=3),
            source_file=source_file,
        )
    book(conn, RANGE, EARLY, date(2022, 12, 30))  # before the last 3 years of history
    book(conn, RANGE, EARLY, date(2026, 1, 10))  # in the latest quarter, not history yet


def seed_search_history(conn: Conn) -> None:
    """A history where every search answer is known: see test_api_search_ranking.py."""
    for year in range(2022, 2026):
        tuesday = date.fromisocalendar(year, 10, 2)
        saturday = date.fromisocalendar(year, 10, 6)
        book(conn, RANGE, "Quiet Creek camping area", tuesday)  # open in March, empty Saturdays
        book(conn, RANGE, "Twin Hollow camping area", tuesday)  # ties with Quiet Creek
        book(conn, RANGE, "Middle Creek camping area", saturday, sites=2)
        book(conn, COAST, "Busy Beach camping area", saturday, sites=10)
        book(conn, RANGE, "Closed Gorge camping area", date(year, 8, 13), sites=5)
    for year in (2024, 2025):  # below MIN_HISTORY
        book(conn, RANGE, "Thin Creek camping area", date.fromisocalendar(year, 10, 2))
    for year in range(2012, 2016):  # not booked since ACTIVE_SINCE
        book(conn, RANGE, "Retired Ridge camping area", date.fromisocalendar(year, 10, 2))
    # The latest quarter isn't history yet; this night makes all of 2025 count.
    book(conn, RANGE, "Quiet Creek camping area", date(2026, 1, 15))
    book(conn, RANGE, "Twin Hollow camping area", date(2026, 1, 15))
    seed_lead_times(conn)
    list(refresh_derived(conn))
    # One campground matched to an OpenStreetMap object, as `qc locations` would; after
    # refresh_derived, which creates the campground rows.
    conn.execute(
        "UPDATE campground SET osm_type = 'way', osm_id = 4242 WHERE name = %s",
        ("Quiet Creek camping area",),
    )


@pytest.fixture(scope="session")
def seeded_settings() -> Iterator[Settings]:
    """Settings for a database seeded once per run; the search tests only read it."""
    url = fresh_database(SEARCH_DB).render_as_string(hide_password=False)
    # The function-scoped `monkeypatch` can't be used by a session fixture.
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DATABASE_URL", url)
        command.upgrade(Config(ALEMBIC_INI), "head")
        with psycopg.connect(psycopg_conninfo()) as conn:
            seed_search_history(conn)  # committed on leaving, so the app's connections see it
        yield Settings(database_url=url)


@pytest.fixture(scope="session")
def seeded_ids(seeded_settings: Settings) -> dict[str, int]:
    """Each seeded campground's id by name, for URLs like /campgrounds/{id}."""
    engine = create_engine(seeded_settings.database_url)
    try:
        with engine.connect() as conn:
            return dict(conn.execute(select(Campground.name, Campground.id)).all())
    finally:
        engine.dispose()


@pytest.fixture
def seeded_client(seeded_settings: Settings) -> Iterator[TestClient]:
    """The API on the seeded search database."""
    with TestClient(create_app(seeded_settings)) as client:
        yield client
