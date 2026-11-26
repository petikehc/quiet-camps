from collections import Counter
from collections.abc import Iterator
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from quiet_camps.db.locations import ACTIVE_SINCE
from quiet_camps.ingest.qpws import QPWS_FILE, load_pages
from quiet_camps.ingest.qpws_match import qpws_link


def has_qpws_pages(locations_dir: Path) -> bool:
    return (locations_dir / QPWS_FILE).exists()


def link_campgrounds(conn: psycopg.Connection[TupleRow], locations_dir: Path) -> Counter[str]:
    """Give every campground its QPWS page, in one transaction. Returns the count per kind.

    Safe to run again: every campground's link is rewritten, to NULL when nothing matches.
    """
    camping, parks = load_pages(locations_dir / QPWS_FILE)
    rows = conn.execute("SELECT id, park_name, name FROM campground ORDER BY id").fetchall()
    links = {cid: qpws_link(park, name, camping, parks) for cid, park, name in rows}
    with conn.transaction(), conn.cursor() as cur:
        cur.executemany(
            "UPDATE campground SET qpws_url = %s, qpws_url_kind = %s WHERE id = %s",
            [
                (link.url, link.kind, cid) if link else (None, None, cid)
                for cid, link in links.items()
            ],
        )
    return Counter(link.kind if link else "none" for link in links.values())


def qpws_report(conn: psycopg.Connection[TupleRow]) -> Iterator[str]:
    """Links per kind for campgrounds in use, then every one without a page."""
    counts = conn.execute(
        "SELECT coalesce(qpws_url_kind, 'none'), count(*) FROM campground"
        " WHERE last_night >= %s GROUP BY 1 ORDER BY 2 DESC",
        (ACTIVE_SINCE,),
    ).fetchall()
    yield f"QPWS pages for campgrounds booked since {ACTIVE_SINCE:%Y}:"
    for kind, n in counts:
        yield f"  {kind:<8} {n:>4}"
    unlinked = conn.execute(
        "SELECT park_name, name FROM campground WHERE last_night >= %s AND qpws_url IS NULL"
        " ORDER BY park_name, name",
        (ACTIVE_SINCE,),
    ).fetchall()
    yield f"\nno page, so the park finder ({len(unlinked)}):"
    for park, name in unlinked:
        yield f"  {park} | {name}"
