from collections.abc import Iterator

import psycopg
from psycopg.rows import TupleRow

from quiet_camps.ingest.campgrounds import Key, campground_key, load_merges, suggest_merges

# Each campground shows the names from its most recently booked area, and that area's last
# night is the campground's.
SET_DISPLAY_NAMES = """
UPDATE campground c SET name = latest.area, park_name = latest.park, last_night = latest.last
FROM (
    SELECT DISTINCT ON (a.campground_id)
        a.campground_id, a.name AS area, p.name AS park, n.last
    FROM camping_area a
    JOIN park p ON p.id = a.park_id
    LEFT JOIN (SELECT area_id, max(night) AS last FROM camp_night GROUP BY area_id) n
        ON n.area_id = a.id
    ORDER BY a.campground_id, n.last DESC NULLS LAST, a.id DESC
) latest
WHERE latest.campground_id = c.id
"""


def assign_campgrounds(
    conn: psycopg.Connection[TupleRow], merges: dict[Key, Key] | None = None
) -> int:
    """Give every camping area its campground, all or nothing. Returns the campground count.

    Safe to run again: a campground keeps its id while any of its names is still in use.
    """
    if merges is None:
        merges = load_merges()
    areas = conn.execute(
        "SELECT a.id, p.name, a.name FROM camping_area a JOIN park p ON p.id = a.park_id"
    ).fetchall()

    with conn.transaction():
        campground_ids: dict[Key, int] = {}
        for area_id, park, area in areas:
            key = campground_key(park, area, merges)
            if key not in campground_ids:
                # The names are placeholders until SET_DISPLAY_NAMES picks the latest ones.
                row = conn.execute(
                    "INSERT INTO campground (park_key, area_key, name, park_name)"
                    " VALUES (%s, %s, %s, %s)"
                    " ON CONFLICT (park_key, area_key) DO UPDATE SET park_key = EXCLUDED.park_key"
                    " RETURNING id",
                    (*key, area, park),
                ).fetchone()
                if row is None:
                    raise RuntimeError("RETURNING gave no row")
                campground_ids[key] = row[0]
            conn.execute(
                "UPDATE camping_area SET campground_id = %s WHERE id = %s",
                (campground_ids[key], area_id),
            )

        # A merge added to the CSV leaves the old campground with no areas.
        conn.execute(
            "DELETE FROM campground c"
            " WHERE NOT EXISTS (SELECT 1 FROM camping_area a WHERE a.campground_id = c.id)"
        )
        conn.execute(SET_DISPLAY_NAMES)
    return len(campground_ids)


def campground_suggestions(conn: psycopg.Connection[TupleRow]) -> Iterator[str]:
    """Likely typos among the campgrounds, as merges-CSV rows to review, best match first."""
    keys: list[Key] = conn.execute("SELECT park_key, area_key FROM campground").fetchall()
    for s in suggest_merges(keys):
        yield f"{s.score:5.1f}  {s.park},{s.area},{s.same_as}"
