from collections.abc import Iterator
from datetime import date
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.rows import TupleRow

from quiet_camps.db.campgrounds import assign_campgrounds
from quiet_camps.db.locations import has_sources, locate_campgrounds
from quiet_camps.ingest.day_kinds import day_kinds
from quiet_camps.timing import timed

FIRST_NIGHT = date(2011, 1, 1)
YEARS_AHEAD = 3  # searches ask about future nights


def fill_calendar(conn: psycopg.Connection[TupleRow], last: date) -> int:
    """Replace calendar_day with every night from 2011 to `last`. Returns the night count."""
    nights = 0
    with conn.transaction():
        conn.execute("DELETE FROM calendar_day")
        with (
            conn.cursor() as cur,
            cur.copy("COPY calendar_day (night, kind, holiday) FROM STDIN") as copy,
        ):
            for day in day_kinds(FIRST_NIGHT, last):
                copy.write_row((day.night, day.kind, day.holiday))
                nights += 1
    return nights


def refresh_derived(conn: psycopg.Connection[TupleRow]) -> Iterator[str]:
    """Rebuild what's derived from camp_night, in order, reporting each step.

    Campgrounds and the calendar first, because campground_typical reads both.
    """
    with timed() as t:
        n = assign_campgrounds(conn)
    yield f"{'campgrounds':<42} {n:>9,} {t.seconds:6.1f}s"

    with timed() as t:
        n = fill_calendar(conn, date(date.today().year + YEARS_AHEAD, 12, 31))
    yield f"{'calendar nights':<42} {n:>9,} {t.seconds:6.1f}s"

    for view in ("area_night", "campground_typical"):  # the second reads the first
        name = sql.Identifier(view)
        with timed() as t, conn.transaction():
            conn.execute(sql.SQL("REFRESH MATERIALIZED VIEW {}").format(name))
            row = conn.execute(sql.SQL("SELECT count(*) FROM {}").format(name)).fetchone()
        rows = row[0] if row else 0
        yield f"{view:<42} {rows:>9,} {t.seconds:6.1f}s"


def refresh_locations(conn: psycopg.Connection[TupleRow], locations_dir: Path) -> Iterator[str]:
    """Re-locate every campground from the downloaded files. Run after refresh_derived."""
    if not has_sources(locations_dir):
        yield f"{'locations':<42} skipped: run `qc locations --fetch` first"
        return
    with timed() as t:
        n = len(locate_campgrounds(conn, locations_dir))
    yield f"{'locations':<42} {n:>9,} {t.seconds:6.1f}s"
