from datetime import date

import psycopg
from psycopg.rows import TupleRow

from quiet_camps.db.campgrounds import assign_campgrounds
from quiet_camps.db.load import ensure_areas

type Conn = psycopg.Connection[TupleRow]

OLD = ("Fraser Island Recreation Area", "Dundubara (Tent Site) camping area")
NEW = ("K'gari (Fraser Island) Recreation Area", "Dundubara camping area")
OTHER = ("K'gari (Fraser Island) Recreation Area", "Central Station camping area")


def add_night(conn: Conn, area_id: int, night: date) -> None:
    conn.execute(
        "INSERT INTO camp_night (area_id, night, booked_on, adults, state, source_file)"
        " VALUES (%s, %s, %s, 2, 'QLD', 'test.csv')",
        (area_id, night, night),
    )


def campground_of(conn: Conn) -> dict[tuple[str, str], tuple[str, str]]:
    """{(park, area) as loaded: (campground park name, campground name)}"""
    rows = conn.execute(
        "SELECT p.name, a.name, c.park_name, c.name FROM camping_area a"
        " JOIN park p ON p.id = a.park_id JOIN campground c ON c.id = a.campground_id"
    ).fetchall()
    return {(park, area): (c_park, c_name) for park, area, c_park, c_name in rows}


def campground_ids(conn: Conn) -> set[int]:
    return {row[0] for row in conn.execute("SELECT id FROM campground")}


def count(conn: Conn) -> int:
    row = conn.execute("SELECT count(*) FROM campground").fetchone()
    assert row is not None
    return row[0]


def test_two_names_of_one_place_share_a_campground(conn: Conn) -> None:
    ensure_areas(conn, [OLD, NEW, OTHER])
    assert assign_campgrounds(conn, {}) == 2
    names = campground_of(conn)
    assert names[OLD] == names[NEW]
    assert names[OTHER] != names[NEW]


def test_a_campground_shows_its_most_recent_names(conn: Conn) -> None:
    # OLD is inserted last, so it has the higher id: only the nights can pick NEW.
    new_id = ensure_areas(conn, [NEW])[NEW]
    old_id = ensure_areas(conn, [OLD])[OLD]
    add_night(conn, old_id, date(2017, 1, 1))
    add_night(conn, new_id, date(2025, 1, 1))
    assign_campgrounds(conn, {})
    assert campground_of(conn)[OLD] == NEW
    assert conn.execute("SELECT last_night FROM campground").fetchone() == (date(2025, 1, 1),)


MAIN_RANGE = "Main Range National Park"
POINT_PURE = (MAIN_RANGE, "Point Pure remote bush camp")
POINT_PURE_RETIRED = (MAIN_RANGE, "Point Pure remote bush camp - OBSELETE")


def test_a_name_marked_retired_gives_way_to_the_places_earlier_name(conn: Conn) -> None:
    ids = ensure_areas(conn, [POINT_PURE, POINT_PURE_RETIRED])
    add_night(conn, ids[POINT_PURE], date(2024, 11, 2))
    add_night(conn, ids[POINT_PURE_RETIRED], date(2025, 5, 4))  # booked later, but retired
    assign_campgrounds(conn, {})

    assert campground_of(conn)[POINT_PURE_RETIRED] == POINT_PURE
    # Its last night is still its latest, whichever name it shows.
    assert conn.execute("SELECT last_night FROM campground").fetchone() == (date(2025, 5, 4),)


def test_a_retired_mark_with_no_other_name_is_taken_off(conn: Conn) -> None:
    areas = [
        (MAIN_RANGE, "Repulse Creek camp (obsolete)"),
        (MAIN_RANGE, "Mount Superbus-South Peak remote bush camp - OBSEL"),
        (MAIN_RANGE, "z_Thorsborne Trail"),
    ]
    ensure_areas(conn, areas)
    assign_campgrounds(conn, {})

    assert sorted(name for _, name in campground_of(conn).values()) == [
        "Mount Superbus-South Peak remote bush camp",
        "Repulse Creek camp",
        "Thorsborne Trail",
    ]


def test_a_name_that_only_contains_the_letters_is_left_alone(conn: Conn) -> None:
    area = (MAIN_RANGE, "Obsel Creek camping area")  # obsel as a word, but not at the end
    ensure_areas(conn, [area])
    assign_campgrounds(conn, {})

    assert campground_of(conn)[area] == area


def test_running_it_again_keeps_the_same_campgrounds(conn: Conn) -> None:
    ensure_areas(conn, [OLD, NEW, OTHER])
    assign_campgrounds(conn, {})
    before = campground_ids(conn)
    assign_campgrounds(conn, {})
    assert campground_ids(conn) == before


def test_a_new_merge_leaves_no_empty_campground_behind(conn: Conn) -> None:
    ensure_areas(conn, [NEW, OTHER])
    assert assign_campgrounds(conn, {}) == 2
    merge = {("kgari", "central station"): ("kgari", "dundubara")}  # wrong, but it's a test
    assert assign_campgrounds(conn, merge) == 1
    assert count(conn) == 1
