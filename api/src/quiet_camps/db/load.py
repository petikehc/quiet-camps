from collections.abc import Iterable

import psycopg
from psycopg.rows import TupleRow


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
