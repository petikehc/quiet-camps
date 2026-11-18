from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, inspect, make_url, text
from sqlalchemy.exc import OperationalError

from quiet_camps.db.config import database_url

ALEMBIC_INI = Path(__file__).parents[1] / "alembic.ini"
TEST_DB = "quiet_camps_test"
TABLES = {"park", "camping_area", "camp_night"}


@pytest.fixture
def test_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    """A fresh, empty database for each test, so migrations never touch your loaded data."""
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
    # env.py asks database_url(), so this points Alembic at the test database.
    monkeypatch.setenv("DATABASE_URL", test_url.render_as_string(hide_password=False))
    engine = create_engine(test_url)
    yield engine
    engine.dispose()


@pytest.fixture
def alembic_cfg() -> Config:
    return Config(ALEMBIC_INI)


def tables(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names()) - {"alembic_version"}


def enum_types(engine: Engine) -> set[str]:
    with engine.connect() as conn:
        return set(conn.scalars(text("SELECT typname FROM pg_type WHERE typtype = 'e'")))


def test_upgrade_creates_the_tables_and_the_enum(test_db: Engine, alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    assert tables(test_db) == TABLES
    assert enum_types(test_db) == {"state"}


def test_migration_matches_the_models(test_db: Engine, alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    # Raises if autogenerate would still find a difference between the models and the database.
    command.check(alembic_cfg)


def test_constraints_follow_the_naming_convention(test_db: Engine, alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    with test_db.connect() as conn:
        names = set(
            conn.scalars(
                text(
                    "SELECT conname FROM pg_constraint"
                    " WHERE conrelid = 'camping_area'::regclass AND contype IN ('p', 'f', 'u')"
                )
            )
        )
    # Without a convention Postgres invents these (camping_area_pkey, ..._fkey, ..._key),
    # and a later migration has to guess them to drop or change one.
    assert names == {"pk_camping_area", "fk_camping_area_park_id_park", "uq_camping_area_park_id"}


def test_downgrade_leaves_nothing_behind(test_db: Engine, alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")
    assert tables(test_db) == set()
    assert enum_types(test_db) == set()


def test_upgrade_works_again_after_a_downgrade(test_db: Engine, alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")
    assert tables(test_db) == TABLES
