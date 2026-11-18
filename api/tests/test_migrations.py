from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect, text

TABLES = {"park", "camping_area", "camp_night"}


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
