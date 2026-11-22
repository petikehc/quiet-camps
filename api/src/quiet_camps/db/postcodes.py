import json
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from quiet_camps.ingest.postcodes import postcode_centroids

POSTCODES_FILE = "postcode_centroids.geojson"


def load_postcodes(conn: psycopg.Connection[TupleRow], path: Path) -> int:
    """Replace postcode_centroid from the downloaded file, in one transaction. Returns the count."""
    centroids = postcode_centroids(json.loads(path.read_text(encoding="utf-8")))
    with conn.transaction(), conn.cursor() as cur:
        cur.execute("DELETE FROM postcode_centroid")
        cur.executemany(
            "INSERT INTO postcode_centroid (postcode, lat, lon) VALUES (%s, %s, %s)",
            [(c.postcode, c.lat, c.lon) for c in centroids],
        )
    return len(centroids)
