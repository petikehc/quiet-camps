from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect, text

TABLES = {
    "park",
    "camping_area",
    "camp_night",
    "campground",
    "calendar_day",
    "park_outline",
    "postcode_centroid",
}


def tables(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names()) - {"alembic_version"}


def enum_types(engine: Engine) -> set[str]:
    with engine.connect() as conn:
        return set(conn.scalars(text("SELECT typname FROM pg_type WHERE typtype = 'e'")))


def materialized_views(engine: Engine) -> set[str]:
    with engine.connect() as conn:
        return set(conn.scalars(text("SELECT matviewname FROM pg_matviews")))


def test_upgrade_creates_the_tables_and_the_enum(test_db: Engine, alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    assert tables(test_db) == TABLES
    assert enum_types(test_db) == {"state"}


def test_upgrade_creates_the_views(test_db: Engine, alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    assert materialized_views(test_db) == {"area_night", "campground_typical"}


def test_area_night_has_one_row_per_area_and_night(test_db: Engine, alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    with test_db.connect() as conn:
        indexes = conn.execute(
            text(
                "SELECT i.relname, ix.indisunique,"
                " array_agg(a.attname::text ORDER BY array_position(ix.indkey, a.attnum))"
                " FROM pg_index ix"
                " JOIN pg_class i ON i.oid = ix.indexrelid"
                " JOIN pg_attribute a ON a.attrelid = ix.indrelid AND a.attnum = ANY(ix.indkey)"
                " WHERE ix.indrelid = 'area_night'::regclass"
                " GROUP BY i.relname, ix.indisunique"
            )
        ).all()
    # Unique, so REFRESH ... CONCURRENTLY works later and a lookup by area and night is one row.
    expected = ("ix_area_night_area_id", True, ["area_id", "night"])
    assert [tuple(row) for row in indexes] == [expected]


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
    assert names == {
        "pk_camping_area",
        "fk_camping_area_park_id_park",
        "fk_camping_area_campground_id_campground",
        "uq_camping_area_park_id",
    }


def test_downgrade_leaves_nothing_behind(test_db: Engine, alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")
    assert tables(test_db) == set()
    assert enum_types(test_db) == set()
    assert materialized_views(test_db) == set()


def test_upgrade_works_again_after_a_downgrade(test_db: Engine, alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")
    assert tables(test_db) == TABLES
