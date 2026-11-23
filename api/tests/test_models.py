from sqlalchemy import Date, Enum, Integer, String, Table, UniqueConstraint

from quiet_camps.db import models
from quiet_camps.ingest.clean import State


def table(name: str) -> Table:
    return models.Base.metadata.tables[name]


def unique_column_sets(t: Table) -> set[frozenset[str]]:
    """Every set of columns the table keeps unique, however it was declared."""
    sets = {
        frozenset(c.name for c in uc.columns)
        for uc in t.constraints
        if isinstance(uc, UniqueConstraint)
    }
    sets |= {frozenset(c.name for c in ix.columns) for ix in t.indexes if ix.unique}
    sets |= {frozenset([c.name]) for c in t.columns if c.unique}
    return sets


def test_the_tables() -> None:
    assert set(models.Base.metadata.tables) == {
        "park",
        "camping_area",
        "camp_night",
        "campground",
        "calendar_day",
        "park_outline",
        "postcode_centroid",
        "place",
    }


def test_a_campground_is_unique_by_its_keys() -> None:
    assert frozenset(["park_key", "area_key"]) in unique_column_sets(table("campground"))


def test_park_name_is_required_and_unique() -> None:
    park = table("park")
    assert not park.c.name.nullable
    assert frozenset(["name"]) in unique_column_sets(park)


def test_area_belongs_to_a_park_and_its_name_is_unique_within_it() -> None:
    area = table("camping_area")
    assert {fk.target_fullname for fk in area.c.park_id.foreign_keys} == {"park.id"}
    assert not area.c.park_id.nullable
    assert not area.c.name.nullable
    # Two parks can both have an area called "Main camping area", one park can't.
    assert frozenset(["park_id", "name"]) in unique_column_sets(area)
    assert frozenset(["name"]) not in unique_column_sets(area)


def test_camp_night_columns_and_which_may_be_missing() -> None:
    nullable = {c.name: c.nullable for c in table("camp_night").columns}
    assert nullable == {
        "id": False,
        "area_id": False,
        "night": False,
        "booked_on": False,
        "adults": True,
        "children": True,
        "infants": True,
        "postcode": True,
        "state": False,
        "reservation_id": True,
        "source_file": False,
    }


def test_camp_night_types() -> None:
    c = table("camp_night").c
    assert {fk.target_fullname for fk in c.area_id.foreign_keys} == {"camping_area.id"}
    assert isinstance(c.night.type, Date)
    assert isinstance(c.booked_on.type, Date)
    for count in (c.adults, c.children, c.infants):
        assert isinstance(count.type, Integer)
    # Postcodes are text ("0810"), never numbers.
    assert isinstance(c.postcode.type, String)
    assert c.postcode.type.length == 4
    assert isinstance(c.state.type, Enum)
    assert c.state.type.enums == [s.value for s in State]
    assert isinstance(c.reservation_id.type, String)
    assert isinstance(c.source_file.type, String)


def test_park_and_area_know_each_other_without_a_database() -> None:
    park = models.Park(name="K'gari (Fraser Island)")
    area = models.CampingArea(name="Central Station", park=park)
    assert park.areas == [area]
    assert area.park is park
