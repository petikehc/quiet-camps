import json
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import LiteralString

import psycopg
from psycopg.rows import TupleRow
from psycopg.types.json import Jsonb

from quiet_camps.ingest.campgrounds import Key
from quiet_camps.ingest.locations import (
    Location,
    Override,
    Source,
    load_overrides,
    locate,
    osm_camps,
    park_outlines,
)

OSM_FILE = "osm_camp_sites.json"
PARKS_FILE = "park_outlines.geojson"
# Campgrounds still in use: the ones a search shows, so the ones worth reviewing.
ACTIVE_SINCE = date(2024, 1, 1)


def has_sources(locations_dir: Path) -> bool:
    return (locations_dir / OSM_FILE).exists() and (locations_dir / PARKS_FILE).exists()


def locate_campgrounds(
    conn: psycopg.Connection[TupleRow],
    locations_dir: Path,
    overrides: dict[Key, Override] | None = None,
) -> list[Location]:
    """Locate every campground from the downloaded files, and save it all in one transaction.

    Safe to run again: the outlines are replaced and every campground's location is rewritten.
    """
    if overrides is None:
        overrides = load_overrides()
    camps = osm_camps(json.loads((locations_dir / OSM_FILE).read_text(encoding="utf-8")))
    outlines = park_outlines(json.loads((locations_dir / PARKS_FILE).read_text(encoding="utf-8")))
    rows = conn.execute("SELECT id, park_key, area_key FROM campground ORDER BY id").fetchall()
    located = locate([(cid, (park, area)) for cid, park, area in rows], camps, outlines, overrides)

    with conn.transaction(), conn.cursor() as cur:
        cur.execute("UPDATE campground SET park_outline_id = NULL")
        cur.execute("DELETE FROM park_outline")
        cur.executemany(
            "INSERT INTO park_outline (id, name, kind, area_ha, geometry)"
            " VALUES (%s, %s, %s, %s, %s)",
            [(o.id, o.name, o.kind, o.area_ha, Jsonb(o.geometry)) for o in outlines],
        )
        cur.executemany(
            "UPDATE campground SET lat = %s, lon = %s, location_source = %s,"
            " location_flags = %s, osm_type = %s, osm_id = %s, osm_name = %s,"
            " match_score = %s, osm_outline = %s, park_outline_id = %s"
            " WHERE id = %s",
            [_row(loc) for loc in located],
        )
    return located


def _row(loc: Location) -> tuple[object, ...]:
    lat, lon = loc.at if loc.at else (None, None)
    camp = loc.camp
    return (
        lat,
        lon,
        loc.source,
        sorted(loc.flags),
        camp.osm_type if camp else None,
        camp.osm_id if camp else None,
        camp.name if camp else None,
        loc.score,
        # Only a matched campsite's outline: a rejected one is somewhere else.
        Jsonb(camp.outline) if camp and camp.outline and loc.source is Source.OSM else None,
        loc.park.id if loc.park else None,
        loc.campground_id,
    )


def location_report(conn: psycopg.Connection[TupleRow], sample: int = 0) -> Iterator[str]:
    """Counts per source and flag for campgrounds in use, then every one that needs a look."""
    active = (ACTIVE_SINCE,)
    total, all_sites = _one(
        conn,
        f"{SITES} SELECT count(*), coalesce(sum(s.sites), 0) FROM campground c {JOIN_SITES}"
        " WHERE c.last_night >= %s",
        active,
    )
    yield f"campgrounds booked since {ACTIVE_SINCE:%Y}: {total}"
    yield f"  {'source':<16} {'campgrounds':>11} {'share':>6} {'of sites':>9}"
    by_source = conn.execute(
        f"{SITES} SELECT coalesce(c.location_source, 'none'), count(*),"
        f" coalesce(sum(s.sites), 0) FROM campground c {JOIN_SITES}"
        " WHERE c.last_night >= %s GROUP BY 1 ORDER BY 2 DESC",
        active,
    ).fetchall()
    for source, n, sites in by_source:
        yield f"  {source:<16} {n:>11} {n / total:>6.0%} {sites / max(all_sites, 1):>9.0%}"

    (clean,) = _one(
        conn,
        "SELECT count(*) FROM campground WHERE last_night >= %s"
        " AND location_source = 'osm' AND location_flags = '{}'",
        active,
    )
    yield f"  clean OSM matches (no flags): {clean}"
    yield "  flags:"
    flags = conn.execute(
        "SELECT flag, count(*) FROM campground, unnest(location_flags) AS flag"
        " WHERE last_night >= %s GROUP BY 1 ORDER BY 2 DESC",
        active,
    ).fetchall()
    for flag, n in flags:
        yield f"    {flag:<16} {n:>4}"

    review = conn.execute(
        "SELECT park_name, name, location_source, location_flags, osm_name, osm_type, osm_id,"
        " match_score FROM campground WHERE last_night >= %s"
        " AND location_flags <> '{}' AND location_flags <> '{reviewed}'"
        " ORDER BY park_name, name",
        active,
    ).fetchall()
    yield f"\nneeds a look ({len(review)}):"
    for park, name, source, row_flags, osm_name, osm_type, osm_id, score in review:
        scored = f" ({score:.0f})" if score is not None else ""  # None when an override picked it
        match = f"{osm_name}{scored} {_osm_url(osm_type, osm_id)}" if osm_name else "-"
        yield f"  {park} | {name} | {source} | {','.join(row_flags)} | {match}"

    if sample:
        rows = conn.execute(
            "SELECT park_name, name, osm_name, osm_type, osm_id FROM campground"
            " WHERE last_night >= %s AND location_source = 'osm' AND location_flags = '{}'"
            " ORDER BY md5(name || id) LIMIT %s",  # random-looking, but the same every run
            (ACTIVE_SINCE, sample),
        ).fetchall()
        yield f"\nsample of clean matches to check by hand ({len(rows)}):"
        for park, name, osm_name, osm_type, osm_id in rows:
            yield f"  {park} | {name} | {osm_name} | {_osm_url(osm_type, osm_id)}"


SITES: LiteralString = (
    "WITH s AS (SELECT a.campground_id, sum(n.sites) AS sites FROM area_night n"
    " JOIN camping_area a ON a.id = n.area_id GROUP BY 1)"
)
JOIN_SITES: LiteralString = "LEFT JOIN s ON s.campground_id = c.id"


def _one(
    conn: psycopg.Connection[TupleRow], query: LiteralString, params: tuple[object, ...]
) -> TupleRow:
    row = conn.execute(query, params).fetchone()
    if row is None:
        raise RuntimeError("an aggregate returned no row")
    return row


def _osm_url(osm_type: str, osm_id: int) -> str:
    return f"https://www.openstreetmap.org/{osm_type}/{osm_id}"
