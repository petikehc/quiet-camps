from datetime import date, timedelta

import psycopg
import pytest
from psycopg.rows import TupleRow

from quiet_camps.db.derived import refresh_derived
from quiet_camps.db.load import ensure_areas

type Conn = psycopg.Connection[TupleRow]

PARK = "K'gari (Fraser Island) Recreation Area"
TENT = (PARK, "Dundubara (Tent Site) camping area")
TRAILER = (PARK, "Dundubara (Trailer Site) camping area")
LATER = (PARK, "Central Station camping area")


def add(conn: Conn, area: tuple[str, str], night: date, sites: int = 1) -> None:
    area_id = ensure_areas(conn, [area])[area]
    for _ in range(sites):  # identical rows in one file are separate sites
        conn.execute(
            "INSERT INTO camp_night (area_id, night, booked_on, adults, children, infants,"
            " state, source_file) VALUES (%s, %s, %s, 2, 0, 0, 'QLD', 'test.csv')",
            (area_id, night, night),
        )


def typical(conn: Conn, kind: str) -> tuple[int, float, float] | None:
    """(nights, sites, busyness) for Dundubara on one kind of night, after a refresh."""
    list(refresh_derived(conn))
    row = conn.execute(
        "SELECT t.nights, t.sites, t.busyness FROM campground_typical t"
        " JOIN campground c ON c.id = t.campground_id"
        " WHERE c.area_key = 'dundubara' AND t.kind = %s",
        (kind,),
    ).fetchone()
    return None if row is None else (row[0], row[1], row[2])


@pytest.fixture(autouse=True)
def history_until_2025(conn: Conn) -> None:
    # The latest quarter is left out, so a night in 2026 makes 2025 part of the history.
    add(conn, LATER, date(2026, 1, 15))


def test_an_unbooked_night_in_an_open_month_counts_as_zero(conn: Conn) -> None:
    add(conn, TENT, date(2023, 3, 11), sites=4)  # Saturday, week 10
    add(conn, TENT, date(2024, 3, 20))  # open in March 2024, but nobody on Saturday 9th
    assert typical(conn, "week 10 6") == (2, 2.0, pytest.approx(2.0))


def test_a_month_with_no_bookings_is_left_out_not_quiet(conn: Conn) -> None:
    add(conn, TENT, date(2023, 3, 11), sites=4)
    add(conn, TENT, date(2024, 3, 9), sites=2)
    # Nothing at all in March 2022 (closed, or unknown): two nights, not three.
    result = typical(conn, "week 10 6")
    assert result is not None
    assert result[:2] == (2, 3.0)


def test_the_covid_closure_is_left_out(conn: Conn) -> None:
    add(conn, TENT, date(2020, 3, 20))  # Friday, before camping closed on 26 March
    assert typical(conn, "week 12 5") is not None
    assert typical(conn, "week 13 6") is None  # Saturday 28 March 2020: closed, not quiet


def test_easter_compares_with_easter_in_other_years(conn: Conn) -> None:
    add(conn, TENT, date(2024, 3, 30), sites=10)  # Easter Saturday 2024
    add(conn, TENT, date(2025, 4, 19), sites=20)  # Easter Saturday 2025
    result = typical(conn, "easter +1")
    assert result is not None
    assert result[:2] == (2, 15.0)


def test_tent_and_trailer_sites_count_together(conn: Conn) -> None:
    add(conn, TENT, date(2023, 3, 11), sites=3)
    add(conn, TRAILER, date(2023, 3, 11), sites=2)
    result = typical(conn, "week 10 6")
    assert result is not None
    assert result[1] == 5.0


def test_busyness_is_against_the_campgrounds_own_busy_nights(conn: Conn) -> None:
    march = [date(2023, 3, 1) + timedelta(days=i) for i in range(31)]
    for night in march:
        add(conn, TENT, night, sites=10 if night == date(2023, 3, 11) else 1)
    # 30 nights of 1 site and one of 10: the 95th-percentile night is 1 site.
    assert typical(conn, "week 10 2") == (1, 1.0, pytest.approx(1.0))  # Tuesday 7 March
    assert typical(conn, "week 10 6") == (1, 10.0, pytest.approx(10.0))


def test_the_latest_quarter_is_left_out(conn: Conn) -> None:
    add(conn, TENT, date(2026, 1, 10))  # in the quarter that's still filling
    assert typical(conn, "week 02 6") is None
