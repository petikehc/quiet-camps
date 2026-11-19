from collections.abc import Iterable
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from quiet_camps.ingest.files import camp_nights

COPY_CAMP_NIGHT = (
    "COPY camp_night (area_id, night, booked_on, adults, children, infants,"
    " postcode, state, reservation_id, source_file) FROM STDIN"
)


def ensure_areas(
    conn: psycopg.Connection[TupleRow], pairs: Iterable[tuple[str, str]]
) -> dict[tuple[str, str], int]:
    area_ids: dict[tuple[str, str], int] = {}
    for park_name, area_name in set(pairs):
        park_row = conn.execute(
            (
                "INSERT INTO park (name) VALUES (%s) "
                "ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id"
            ),
            (park_name,),
        ).fetchone()
        if park_row is None:
            raise RuntimeError("RETURNING gave no row")

        park_id = park_row[0]
        area_row = conn.execute(
            (
                "INSERT INTO camping_area (park_id, name) VALUES (%s, %s) "
                "ON CONFLICT (park_id, name) DO UPDATE SET name = EXCLUDED.name RETURNING id"
            ),
            (
                park_id,
                area_name,
            ),
        ).fetchone()

        if area_row is None:
            raise RuntimeError("RETURNING gave no row")

        area_id = area_row[0]
        area_ids[(park_name, area_name)] = area_id
    return area_ids


def load_file(conn: psycopg.Connection[TupleRow], path: Path) -> int:
    """Copy every night in one permit file into camp_night, all or nothing. Returns the count."""
    copied = 0
    with conn.transaction():
        # A generator runs once, and upserts can't run while COPY streams, so the file is
        # parsed twice: once for the areas, once for the rows. Memory stays flat.
        area_ids = ensure_areas(conn, ((n.park, n.area) for n in camp_nights(path)))
        with conn.cursor() as cur, cur.copy(COPY_CAMP_NIGHT) as copy:
            for n in camp_nights(path):
                copy.write_row(
                    (
                        area_ids[(n.park, n.area)],
                        n.night,
                        n.booked_on,
                        n.adults,
                        n.children,
                        n.infants,
                        n.postcode,
                        n.state,
                        n.reservation_id,
                        path.name,
                    )
                )
                copied += 1
    return copied
