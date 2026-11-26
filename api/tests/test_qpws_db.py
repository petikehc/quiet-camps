import json
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from quiet_camps.db.campgrounds import assign_campgrounds
from quiet_camps.db.derived import refresh_locations
from quiet_camps.db.load import ensure_areas
from quiet_camps.db.qpws import link_campgrounds, qpws_report
from quiet_camps.ingest.qpws import QPWS_FILE

type Conn = psycopg.Connection[TupleRow]

PARKS = "https://parks.qld.gov.au/parks/"
POPLAR = ("Main Range National Park", "Poplar Flat camping area")
SPICERS = ("Main Range National Park", "Spicers Gap camping area")
STEAMER = ("Main Range National Park", "Steamer Creek remote bush camp")
PERCY = ("Percy Isles National Park", "North West Beach")


def write_pages(directory: Path) -> Path:
    camping = [
        {
            "url": f"{PARKS}main-range/camping/poplar-flat",
            "name": "Poplar Flat camping area",
            "park_name": "Main Range National Park",
        }
    ]
    parks = [{"url": f"{PARKS}main-range", "name": "Main Range National Park"}]
    saved = {
        "camping": {"captured": "20261026034219", "pages": camping},
        "parks": {"captured": "20260915045150", "pages": parks},
    }
    (directory / QPWS_FILE).write_text(json.dumps(saved), encoding="utf-8")
    return directory


def links(conn: Conn) -> dict[str, tuple[str | None, str | None]]:
    rows = conn.execute("SELECT name, qpws_url, qpws_url_kind FROM campground").fetchall()
    return {name: (url, kind) for name, url, kind in rows}


def book_recently(conn: Conn, areas: dict[tuple[str, str], int]) -> None:
    for area_id in areas.values():
        conn.execute(
            "INSERT INTO camp_night (area_id, night, booked_on, adults, state, source_file)"
            " VALUES (%s, '2025-06-01', '2025-05-01', 2, 'QLD', 'test.csv')",
            (area_id,),
        )


def test_each_campground_gets_its_camping_page_its_park_page_or_none(
    conn: Conn, tmp_path: Path
) -> None:
    ensure_areas(conn, [POPLAR, STEAMER, PERCY])
    assign_campgrounds(conn, {})

    counts = link_campgrounds(conn, write_pages(tmp_path))

    assert links(conn) == {
        POPLAR[1]: (f"{PARKS}main-range/camping/poplar-flat", "camping"),
        STEAMER[1]: (f"{PARKS}main-range", "park"),
        PERCY[1]: (None, None),  # no page for it or its park
    }
    assert counts == {"camping": 1, "park": 1, "none": 1}


def test_linking_again_clears_a_link_that_no_longer_matches(conn: Conn, tmp_path: Path) -> None:
    ensure_areas(conn, [PERCY])
    assign_campgrounds(conn, {})
    conn.execute("UPDATE campground SET qpws_url = 'https://example.org', qpws_url_kind = 'park'")

    link_campgrounds(conn, write_pages(tmp_path))

    assert links(conn) == {PERCY[1]: (None, None)}


def test_refresh_links_once_the_pages_are_downloaded(conn: Conn, tmp_path: Path) -> None:
    ensure_areas(conn, [POPLAR])
    assign_campgrounds(conn, {})

    lines = list(refresh_locations(conn, write_pages(tmp_path)))

    assert "QPWS pages" in lines[1] and "skipped" not in lines[1]
    assert links(conn)[POPLAR[1]][1] == "camping"


def test_the_report_counts_each_kind_and_lists_campgrounds_without_a_page(
    conn: Conn, tmp_path: Path
) -> None:
    book_recently(conn, ensure_areas(conn, [POPLAR, SPICERS, STEAMER, PERCY]))
    assign_campgrounds(conn, {})
    link_campgrounds(conn, write_pages(tmp_path))

    report = "\n".join(qpws_report(conn))

    assert "  park        2" in report  # Spicers Gap and Steamer Creek
    assert "  camping     1" in report
    assert (
        "no page, so the park finder (1):\n  Percy Isles National Park | North West Beach" in report
    )
