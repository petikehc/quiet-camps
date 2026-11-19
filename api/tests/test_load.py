from datetime import date
from pathlib import Path

import psycopg
import pytest
from psycopg import sql
from psycopg.rows import TupleRow

from quiet_camps.db.config import psycopg_conninfo
from quiet_camps.db.load import ensure_areas, load_file

type Conn = psycopg.Connection[TupleRow]

# A family B (one row per night) file, as in test_files.py.
HEADER_B = (
    "Reservation Number,Type,Postcode,State,Booking Date,Start Date,Stay Date,"
    "Park,Facility,Adults,Children,Infants"
)
POVERTY_CREEK = "Bribie Island NP,Poverty Creek"


def count(conn: Conn, table: str) -> int:
    # A table name can't be a %s parameter, so sql.Identifier quotes it safely instead.
    row = conn.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))).fetchone()
    assert row is not None
    return row[0]


def test_every_pair_gets_an_id(conn: Conn) -> None:
    pairs = [("Bribie Island", "Gallagher Point"), ("Bribie Island", "Poverty Creek")]
    ids = ensure_areas(conn, pairs)
    assert set(ids) == set(pairs)
    assert len(set(ids.values())) == 2
    assert count(conn, "park") == 1
    assert count(conn, "camping_area") == 2


def test_the_ids_are_the_rows_in_the_database(conn: Conn) -> None:
    ids = ensure_areas(conn, [("Bribie Island", "Poverty Creek")])
    row = conn.execute(
        "SELECT p.name, a.name FROM camping_area a JOIN park p ON p.id = a.park_id WHERE a.id = %s",
        (ids[("Bribie Island", "Poverty Creek")],),
    ).fetchone()
    assert row == ("Bribie Island", "Poverty Creek")


def test_the_same_area_name_in_two_parks_is_two_areas(conn: Conn) -> None:
    ids = ensure_areas(conn, [("Park A", "Beach camping"), ("Park B", "Beach camping")])
    assert ids[("Park A", "Beach camping")] != ids[("Park B", "Beach camping")]


def test_repeats_in_the_input_are_fine(conn: Conn) -> None:
    pairs = [("Bribie Island", "Poverty Creek")] * 3
    assert len(ensure_areas(conn, pairs)) == 1
    assert count(conn, "camping_area") == 1


def test_a_second_call_returns_the_same_ids_and_adds_nothing(conn: Conn) -> None:
    pairs = [("Bribie Island", "Poverty Creek"), ("Moreton Island", "The Wrecks")]
    first = ensure_areas(conn, pairs)
    # One new area in a park that already exists, as the next file might bring.
    second = ensure_areas(conn, [*pairs, ("Moreton Island", "Ben-Ewa")])
    assert {pair: second[pair] for pair in pairs} == first
    assert count(conn, "park") == 2
    assert count(conn, "camping_area") == 3


def test_names_with_quotes_are_data_not_sql(conn: Conn) -> None:
    # Real park names have apostrophes. A name glued into the SQL string would break here.
    ids = ensure_areas(conn, [("K'gari (Fraser Island)", "Central Station")])
    assert ("K'gari (Fraser Island)", "Central Station") in ids


def test_nothing_in_nothing_out(conn: Conn) -> None:
    assert ensure_areas(conn, []) == {}
    assert count(conn, "park") == 0


def test_the_caller_owns_the_transaction(conn: Conn) -> None:
    # The loader decides when to commit, so a failed file can roll back its areas too.
    ensure_areas(conn, [("Bribie Island", "Poverty Creek")])
    conn.rollback()
    assert count(conn, "park") == 0
    assert count(conn, "camping_area") == 0


def write_b(path: Path, *rows: str) -> Path:
    path.write_text("\r\n".join([HEADER_B, *rows]) + "\r\n", encoding="utf-8-sig")
    return path


def test_load_file_copies_every_night_with_its_area_and_file(conn: Conn, tmp_path: Path) -> None:
    path = write_b(
        tmp_path / "q1.csv",
        f"576013,Camping,4507,QLD,1/02/2018,31/03/2018,31/03/2018,{POVERTY_CREEK},2,1,0",
        f"576013,Camping,4507,QLD,1/02/2018,31/03/2018,1/04/2018,{POVERTY_CREEK},2,1,0",
        "601222,Camping,,NSW,3/03/2018,1/04/2018,1/04/2018,Moreton Island NP,The Wrecks,,,",
    )

    assert load_file(conn, path) == 3

    rows = conn.execute(
        "SELECT p.name, a.name, n.night, n.booked_on, n.adults, n.children, n.infants,"
        " n.postcode, n.state::text, n.reservation_id, n.source_file"
        " FROM camp_night n"
        " JOIN camping_area a ON a.id = n.area_id JOIN park p ON p.id = a.park_id"
        " ORDER BY n.night, p.name"
    ).fetchall()
    bribie = ("Bribie Island NP", "Poverty Creek")
    assert rows == [
        (*bribie, date(2018, 3, 31), date(2018, 2, 1), 2, 1, 0, "4507", "QLD", "576013", "q1.csv"),
        (*bribie, date(2018, 4, 1), date(2018, 2, 1), 2, 1, 0, "4507", "QLD", "576013", "q1.csv"),
        # Blanks arrive as NULL, not 0 or "".
        (
            *("Moreton Island NP", "The Wrecks", date(2018, 4, 1), date(2018, 3, 3)),
            *(None, None, None, None, "NSW", "601222", "q1.csv"),
        ),
    ]


def test_load_file_commits(conn: Conn, tmp_path: Path) -> None:
    path = write_b(
        tmp_path / "q1.csv",
        f"576013,Camping,4507,QLD,1/02/2018,31/03/2018,31/03/2018,{POVERTY_CREEK},2,0,0",
    )
    load_file(conn, path)

    # A second connection only sees committed rows.
    with psycopg.connect(psycopg_conninfo()) as other:
        assert count(other, "camp_night") == 1


def test_two_files_share_the_park_and_area(conn: Conn, tmp_path: Path) -> None:
    row = f"576013,Camping,4507,QLD,1/02/2018,31/03/2018,{{night}},{POVERTY_CREEK},2,0,0"
    load_file(conn, write_b(tmp_path / "q1.csv", row.format(night="31/03/2018")))
    load_file(conn, write_b(tmp_path / "q2.csv", row.format(night="1/04/2018")))

    assert count(conn, "camping_area") == 1
    assert count(conn, "camp_night") == 2


def test_a_file_that_fails_part_way_leaves_nothing_behind(conn: Conn, tmp_path: Path) -> None:
    # Make the database reject the last night, after the areas and the first nights went in.
    conn.execute("ALTER TABLE camp_night ADD CONSTRAINT test_no_huge_parties CHECK (adults < 50)")
    conn.commit()
    path = write_b(
        tmp_path / "q1.csv",
        f"576013,Camping,4507,QLD,1/02/2018,31/03/2018,31/03/2018,{POVERTY_CREEK},2,0,0",
        "601222,Camping,4000,QLD,3/03/2018,1/04/2018,1/04/2018,Moreton Island NP,The Wrecks,99,0,0",
    )

    with pytest.raises(psycopg.errors.CheckViolation):
        load_file(conn, path)

    assert count(conn, "camp_night") == 0
    assert count(conn, "camping_area") == 0
    assert count(conn, "park") == 0
