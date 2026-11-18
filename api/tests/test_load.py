import psycopg
from psycopg import sql
from psycopg.rows import TupleRow

from quiet_camps.db.load import ensure_areas

type Conn = psycopg.Connection[TupleRow]


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
