from datetime import date

import psycopg
from psycopg.rows import TupleRow

from quiet_camps.db.load import ensure_areas

type Conn = psycopg.Connection[TupleRow]

NIGHT = date(2018, 4, 1)
BOOKED = date(2018, 1, 15)
APR_JUN = "apr18-jun18.csv"
JUL_SEP = "jul18-sep18.csv"


def area(conn: Conn, name: str = "Poverty Creek") -> int:
    return ensure_areas(conn, [("Bribie Island", name)])[("Bribie Island", name)]


def add(
    conn: Conn,
    area_id: int,
    source_file: str,
    *,
    night: date = NIGHT,
    reservation_id: str | None = None,
    adults: int | None = 2,
    children: int | None = 0,
    infants: int | None = 0,
    booked_on: date = BOOKED,
) -> None:
    """One camp_night row: one site (or one booking, before 2016) on one night."""
    conn.execute(
        "INSERT INTO camp_night (area_id, night, booked_on, adults, children, infants,"
        " postcode, state, reservation_id, source_file)"
        " VALUES (%s, %s, %s, %s, %s, %s, '4000', 'QLD', %s, %s)",
        (area_id, night, booked_on, adults, children, infants, reservation_id, source_file),
    )


def area_nights(conn: Conn) -> dict[tuple[int, date], tuple[int, int]]:
    """{(area_id, night): (sites, campers)}, after refreshing the view."""
    conn.execute("REFRESH MATERIALIZED VIEW area_night")
    rows = conn.execute("SELECT area_id, night, sites, campers FROM area_night").fetchall()
    return {(area_id, night): (sites, campers) for area_id, night, sites, campers in rows}


def test_one_site_on_one_night(conn: Conn) -> None:
    a = area(conn)
    add(conn, a, APR_JUN, adults=2, children=1)
    assert area_nights(conn) == {(a, NIGHT): (1, 3)}


def test_campers_count_children_and_infants_and_blanks_count_as_nobody(conn: Conn) -> None:
    a = area(conn)
    add(conn, a, APR_JUN, adults=2, children=2, infants=1)
    add(conn, a, APR_JUN, adults=None, children=None, infants=None)  # "no party size"
    assert area_nights(conn) == {(a, NIGHT): (2, 5)}


def test_identical_rows_in_one_file_are_separate_sites(conn: Conn) -> None:
    a = area(conn)
    add(conn, a, APR_JUN, reservation_id="576013")
    add(conn, a, APR_JUN, reservation_id="576013")
    add(conn, a, APR_JUN)  # no ID: two identical rows are still two sites
    add(conn, a, APR_JUN)
    assert area_nights(conn) == {(a, NIGHT): (4, 8)}


def test_the_same_booking_in_two_files_counts_once(conn: Conn) -> None:
    # Reservation 576013 (ADR 0001): 3 sites, 22 campers, in two quarterly files.
    a = area(conn)
    for source_file in (APR_JUN, JUL_SEP):
        for adults in (8, 7, 7):
            add(conn, a, source_file, reservation_id="576013", adults=adults)
    assert area_nights(conn) == {(a, NIGHT): (3, 22)}


def test_the_same_booking_without_an_id_in_two_files_counts_once(conn: Conn) -> None:
    # 2025-26: a stay across a quarter boundary is in both quarters' files.
    a = area(conn)
    for source_file in (APR_JUN, JUL_SEP):
        add(conn, a, source_file)
        add(conn, a, source_file)
    assert area_nights(conn) == {(a, NIGHT): (2, 4)}


def test_when_files_disagree_on_the_number_of_sites_the_larger_wins(conn: Conn) -> None:
    a = area(conn)
    for _ in range(2):
        add(conn, a, APR_JUN, reservation_id="576013")
    for _ in range(3):
        add(conn, a, JUL_SEP, reservation_id="576013")
    assert area_nights(conn) == {(a, NIGHT): (3, 6)}


def test_different_bookings_on_the_same_night_add_up(conn: Conn) -> None:
    a = area(conn)
    add(conn, a, APR_JUN, reservation_id="1")
    add(conn, a, APR_JUN, reservation_id="2")
    add(conn, a, APR_JUN, booked_on=date(2018, 2, 1))  # no ID, booked on another day
    assert area_nights(conn) == {(a, NIGHT): (3, 6)}


def test_areas_and_nights_stay_separate(conn: Conn) -> None:
    a, b = area(conn, "Poverty Creek"), area(conn, "Gallagher Point")
    next_night = date(2018, 4, 2)
    add(conn, a, APR_JUN)
    add(conn, a, APR_JUN, night=next_night)
    add(conn, b, APR_JUN)
    assert area_nights(conn) == {
        (a, NIGHT): (1, 2),
        (a, next_night): (1, 2),
        (b, NIGHT): (1, 2),
    }


def test_a_booking_the_files_describe_differently_counts_twice(conn: Conn) -> None:
    # The known cost of option A: the copies don't match, so both count (+319 sites of 4.6M).
    a = area(conn)
    add(conn, a, APR_JUN, reservation_id="576013", adults=2)
    add(conn, a, JUL_SEP, reservation_id="576013", adults=3)
    assert area_nights(conn) == {(a, NIGHT): (2, 5)}
