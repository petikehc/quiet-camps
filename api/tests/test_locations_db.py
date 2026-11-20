import json
from pathlib import Path

import psycopg
from psycopg.rows import TupleRow

from quiet_camps.db.campgrounds import assign_campgrounds
from quiet_camps.db.derived import refresh_locations
from quiet_camps.db.load import ensure_areas
from quiet_camps.db.locations import OSM_FILE, PARKS_FILE, locate_campgrounds, location_report
from quiet_camps.ingest.locations import Override

type Conn = psycopg.Connection[TupleRow]

POPLAR = ("Main Range National Park", "Poplar Flat camping area")
STINSON = ("Main Range National Park", "Stinson remote bush camp")
SQUARE = [[152.35, -28.05], [152.45, -28.05], [152.45, -27.95], [152.35, -27.95], [152.35, -28.05]]


def write_sources(directory: Path) -> Path:
    """One park, its anchor campsite, and a campsite 2 km outside it."""
    overpass = {
        "elements": [
            {
                "type": "way",
                "id": 30914330,
                "bounds": {
                    "minlat": -28.001,
                    "minlon": 152.4,
                    "maxlat": -27.999,
                    "maxlon": 152.402,
                },
                "geometry": [
                    {"lat": -28.001, "lon": 152.4},
                    {"lat": -28.001, "lon": 152.402},
                    {"lat": -27.999, "lon": 152.402},
                    {"lat": -28.001, "lon": 152.4},
                ],
                "tags": {"name": "Poplar Flat Campground"},
            },
            {
                "type": "node",
                "id": 7,
                "lat": -28.0,
                "lon": 152.47,
                "tags": {"name": "Stinson Memorial Park"},
            },
        ]
    }
    parks = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "objectid": 501,
                    "estatename": "Main Range National Park",
                    "esttype": "NP",
                    "latitude": -28.0,
                    "longitude": 152.4,
                    "gazareaha": 38282.8,
                },
                "geometry": {"type": "Polygon", "coordinates": [SQUARE]},
            }
        ],
    }
    (directory / OSM_FILE).write_text(json.dumps(overpass), encoding="utf-8")
    (directory / PARKS_FILE).write_text(json.dumps(parks), encoding="utf-8")
    return directory


def locations(conn: Conn) -> dict[str, tuple[object, ...]]:
    rows = conn.execute(
        "SELECT name, location_source, location_flags, osm_id, osm_outline IS NOT NULL,"
        " park_outline_id FROM campground"
    ).fetchall()
    return {name: tuple(rest) for name, *rest in rows}


def test_locations_are_saved_with_their_source_flags_and_outlines(
    conn: Conn, tmp_path: Path
) -> None:
    ensure_areas(conn, [POPLAR, STINSON])
    assign_campgrounds(conn, {})
    locate_campgrounds(conn, write_sources(tmp_path), overrides={})

    assert locations(conn) == {
        POPLAR[1]: ("osm", [], 30914330, True, 501),
        # Rejected (2 km outside), so the park centre, but the rejected campsite is kept.
        STINSON[1]: ("park_osm", ["contains", "rejected_osm"], 7, False, 501),
    }
    assert conn.execute("SELECT id, name FROM park_outline").fetchall() == [
        (501, "Main Range National Park")
    ]


def test_locating_again_changes_nothing(conn: Conn, tmp_path: Path) -> None:
    ensure_areas(conn, [POPLAR, STINSON])
    assign_campgrounds(conn, {})
    sources = write_sources(tmp_path)
    locate_campgrounds(conn, sources, overrides={})
    before = locations(conn)
    locate_campgrounds(conn, sources, overrides={})
    assert locations(conn) == before


def test_refresh_skips_locations_until_the_files_are_downloaded(conn: Conn, tmp_path: Path) -> None:
    lines = list(refresh_locations(conn, tmp_path))
    assert len(lines) == 1
    assert "qc locations --fetch" in lines[0]


def test_the_report_lists_what_needs_a_look(conn: Conn, tmp_path: Path) -> None:
    areas = ensure_areas(conn, [POPLAR, STINSON])
    for area_id in areas.values():
        conn.execute(
            "INSERT INTO camp_night (area_id, night, booked_on, adults, state, source_file)"
            " VALUES (%s, '2025-06-01', '2025-05-01', 2, 'QLD', 'test.csv')",
            (area_id,),
        )
    assign_campgrounds(conn, {})
    conn.execute("REFRESH MATERIALIZED VIEW area_night")
    locate_campgrounds(conn, write_sources(tmp_path), overrides={})

    report = "\n".join(location_report(conn, sample=5))
    assert "campgrounds booked since 2024: 2" in report
    assert "clean OSM matches (no flags): 1" in report
    assert "needs a look (1):" in report
    assert (
        "Stinson remote bush camp | park_osm | contains,rejected_osm | Stinson Memorial Park"
        in report
    )
    assert "https://www.openstreetmap.org/node/7" in report
    assert "Poplar Flat camping area | Poplar Flat Campground" in report  # the sample


def test_the_report_shows_an_override_without_a_score(conn: Conn, tmp_path: Path) -> None:
    areas = ensure_areas(conn, [POPLAR, STINSON])
    for area_id in areas.values():
        conn.execute(
            "INSERT INTO camp_night (area_id, night, booked_on, adults, state, source_file)"
            " VALUES (%s, '2025-06-01', '2025-05-01', 2, 'QLD', 'test.csv')",
            (area_id,),
        )
    assign_campgrounds(conn, {})
    conn.execute("REFRESH MATERIALIZED VIEW area_night")
    # A reviewer points Stinson at Poplar Flat's campsite (wrong, but it's a test), so both
    # share a point: the review list shows Stinson's match with no score.
    overrides = {("main range", "stinson bush"): Override(("way", 30914330), None)}
    locate_campgrounds(conn, write_sources(tmp_path), overrides=overrides)

    assert locations(conn)[STINSON[1]] == ("osm", ["reviewed", "shared_point"], 30914330, True, 501)
    report = "\n".join(location_report(conn))
    assert "needs a look (2):" in report
    assert (
        "Stinson remote bush camp | osm | reviewed,shared_point | Poplar Flat Campground "
        "https://www.openstreetmap.org/way/30914330"
    ) in report
