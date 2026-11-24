import json
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from quiet_camps.ingest.places import abs_places

PLACES_FILE = "abs_places.json"  # {"localities": GeoJSON, "councils": GeoJSON}


def load_places(conn: psycopg.Connection[TupleRow], path: Path) -> int:
    """Replace place from the downloaded file, in one transaction. Returns the count."""
    fetched = json.loads(path.read_text(encoding="utf-8"))
    places = abs_places(fetched["localities"], "sal_name_2021", "locality") + abs_places(
        fetched["councils"], "lga_name_2021", "council"
    )
    with conn.transaction(), conn.cursor() as cur:
        cur.execute("DELETE FROM place")
        cur.executemany(
            "INSERT INTO place (name, kind, lat, lon) VALUES (%s, %s, %s, %s)",
            [(p.name, p.kind, p.lat, p.lon) for p in places],
        )
    return len(places)
