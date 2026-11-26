import argparse
import json
import time
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

import httpx
import psycopg

from quiet_camps.api.openapi import OPENAPI_FILE, openapi_document
from quiet_camps.db.campgrounds import campground_suggestions
from quiet_camps.db.config import psycopg_conninfo
from quiet_camps.db.derived import refresh_derived, refresh_locations
from quiet_camps.db.load import load_all
from quiet_camps.db.locations import OSM_FILE, PARKS_FILE, has_sources, location_report
from quiet_camps.db.places import PLACES_FILE, load_places
from quiet_camps.db.postcodes import POSTCODES_FILE, load_postcodes
from quiet_camps.db.qpws import has_qpws_pages, link_campgrounds, qpws_report
from quiet_camps.ingest.ckan import PackageShowResponse, camping_csv_urls
from quiet_camps.ingest.download import download_csv
from quiet_camps.ingest.profile_report import profile
from quiet_camps.ingest.qpws import (
    CAMPGROUNDS_A_Z,
    PARKS_A_Z,
    QPWS_FILE,
    camping_pages,
    park_pages,
)
from quiet_camps.ingest.quality_report import quality
from quiet_camps.ingest.retry import retry

PACKAGE_URL = "https://www.data.qld.gov.au/api/3/action/package_show"
PACKAGE_ID = "camping-and-vehicle-permits"
USER_AGENT = "quiet-camps/0.1 (learning project)"
# src/quiet_camps/cli.py → repo root. Works because uv installs the package in editable mode.
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"
DEFAULT_LOCATIONS_DIR = DEFAULT_DATA_DIR.parent / "locations"
PAUSE_BETWEEN_DOWNLOADS = 0.5

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# Every named campsite in Queensland; `out geom` adds the outline of those drawn as an area.
OVERPASS_QUERY = """[out:json][timeout:180];
area["ISO3166-2"="AU-QLD"]->.qld;
nwr["tourism"="camp_site"]["name"](area.qld);
out geom;"""
PARKS_URL = (
    "https://spatial-gis.information.qld.gov.au/arcgis/rest/services/Environment/"
    "ParksTerrestrialProtectedAreas/MapServer/10/query"
)
PARKS_PAGE = 1000
# Centres of ABS ASGS 2021 areas (CC BY 4.0): postal areas, for where campers come from;
# suburbs and localities, and council areas, for "near Noosa" and "from Toowoomba".
ABS_POINTS = "https://geo.abs.gov.au/arcgis/rest/services/ASGS2021/{}/MapServer/2/query"
POSTCODES_URL = ABS_POINTS.format("POA")
LOCALITIES_URL = ABS_POINTS.format("SAL")
COUNCILS_URL = ABS_POINTS.format("LGA")
ABS_PAGE = 2000  # the service's most per request
# parks.qld.gov.au turns scripts away (Cloudflare), so its listings come from the Internet Archive.
WAYBACK_CDX = "https://web.archive.org/cdx/search/cdx"
WAYBACK_RAW = "https://web.archive.org/web/{timestamp}id_/{url}"  # id_: the page as captured


def is_transient(exc: Exception) -> bool:
    """Worth retrying: network failures, rate limits and server errors. Not 404s."""
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status == 429 or status >= 500
    return isinstance(exc, httpx.TransportError)


download_with_retry = retry(attempts=4, delay=2.0, retry_if=is_transient)(download_csv)


@retry(attempts=4, delay=2.0, retry_if=is_transient)
def fetch_package(client: httpx.Client) -> PackageShowResponse:
    response = client.get(PACKAGE_URL, params={"id": PACKAGE_ID})
    response.raise_for_status()
    package: PackageShowResponse = response.json()
    if not package["success"]:
        raise RuntimeError(f"CKAN package_show failed for {PACKAGE_ID}")
    return package


@retry(attempts=4, delay=10.0, retry_if=is_transient)
def fetch_osm_camp_sites(client: httpx.Client) -> dict[str, Any]:
    response = client.post(OVERPASS_URL, data={"data": OVERPASS_QUERY}, timeout=240)
    response.raise_for_status()
    return response.json()


@retry(attempts=4, delay=2.0, retry_if=is_transient)
def fetch_park_outlines_page(client: httpx.Client, offset: int) -> dict[str, Any]:
    params: dict[str, str | float] = {
        "where": "1=1",
        "outFields": "objectid,estatename,esttype,latitude,longitude,gazareaha",
        "outSR": 4326,  # longitude and latitude, as GeoJSON wants
        "maxAllowableOffset": 0.001,  # simplify to about 100 m: 2 MB instead of 100+
        "geometryPrecision": 5,
        "orderByFields": "objectid",
        "resultOffset": offset,
        "resultRecordCount": PARKS_PAGE,
        "f": "geojson",
    }
    response = client.get(PARKS_URL, params=params)
    response.raise_for_status()
    return response.json()


def fetch_park_outlines(client: httpx.Client) -> dict[str, Any]:
    """Every protected area, one page at a time."""
    features: list[Any] = []
    while True:
        page = fetch_park_outlines_page(client, len(features))
        features += page["features"]
        if len(page["features"]) < PARKS_PAGE:
            return {"type": "FeatureCollection", "features": features}


@retry(attempts=4, delay=2.0, retry_if=is_transient)
def fetch_abs_points_page(
    client: httpx.Client, url: str, field: str, where: str, offset: int
) -> dict[str, Any]:
    params: dict[str, str | float] = {
        "where": where,
        "outFields": f"{field},state_code_2021",
        "outSR": 4326,
        "geometryPrecision": 4,  # about 10 m: an area's centre is a rough place anyway
        "orderByFields": "objectid",
        "resultOffset": offset,
        "resultRecordCount": ABS_PAGE,
        "f": "geojson",
    }
    response = client.get(url, params=params)
    response.raise_for_status()
    return response.json()


def fetch_abs_points(
    client: httpx.Client, url: str, field: str, where: str = "1=1"
) -> dict[str, Any]:
    """Every area's centre from an ABS point service, one page at a time."""
    features: list[Any] = []
    while True:
        page = fetch_abs_points_page(client, url, field, where, len(features))
        features += page["features"]
        if len(page["features"]) < ABS_PAGE:
            return {"type": "FeatureCollection", "features": features}


def fetch_postcodes(client: httpx.Client) -> dict[str, Any]:
    return fetch_abs_points(client, POSTCODES_URL, "poa_code_2021")


def fetch_places(client: httpx.Client) -> dict[str, Any]:
    """Queensland's suburbs and localities, and its council areas."""
    queensland = "state_code_2021 = '3'"
    return {
        "localities": fetch_abs_points(client, LOCALITIES_URL, "sal_name_2021", queensland),
        "councils": fetch_abs_points(client, COUNCILS_URL, "lga_name_2021", queensland),
    }


@retry(attempts=4, delay=10.0, retry_if=is_transient)
def fetch_latest_capture(client: httpx.Client, url: str) -> tuple[str, str]:
    """The Internet Archive's latest good capture of a page: (its timestamp, its HTML)."""
    params = {"url": url, "filter": "statuscode:200", "fl": "timestamp", "output": "json"}
    response = client.get(WAYBACK_CDX, params={**params, "limit": "-1"})  # -1: the last one
    response.raise_for_status()
    rows: list[list[str]] = response.json()  # a header row, then one row per capture
    if len(rows) < 2:
        raise RuntimeError(f"The Internet Archive has no capture of {url}")
    timestamp = rows[-1][0]
    page = client.get(WAYBACK_RAW.format(timestamp=timestamp, url=url))
    page.raise_for_status()
    return timestamp, page.text


def fetch_qpws_pages(client: httpx.Client) -> dict[str, Any]:
    """Every QPWS camping area's page and park's page, from the two A to Z listings."""
    camping_at, camping_html = fetch_latest_capture(client, CAMPGROUNDS_A_Z)
    parks_at, parks_html = fetch_latest_capture(client, PARKS_A_Z)
    return {
        "camping": {
            "captured": camping_at,
            "pages": [asdict(p) for p in camping_pages(camping_html)],
        },
        "parks": {"captured": parks_at, "pages": [asdict(p) for p in park_pages(parks_html)]},
    }


def save_qpws_pages(locations_dir: Path) -> bool:
    with httpx.Client(
        headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=120
    ) as client:
        pages = fetch_qpws_pages(client)
    camping, parks = pages["camping"], pages["parks"]
    if not camping["pages"] or not parks["pages"]:
        print("Found no pages: has the layout of the A to Z listings changed?")
        return False
    locations_dir.mkdir(parents=True, exist_ok=True)
    (locations_dir / QPWS_FILE).write_text(json.dumps(pages, indent=1), encoding="utf-8")
    print(
        f"{len(camping['pages'])} camping area pages (captured {camping['captured'][:8]}) and "
        f"{len(parks['pages'])} park pages (captured {parks['captured'][:8]}) from "
        "parks.qld.gov.au, via the Internet Archive"
    )
    return True


def qpws_pages_command(locations_dir: Path, fetch: bool) -> int:
    if fetch and not save_qpws_pages(locations_dir):
        return 1
    if not has_qpws_pages(locations_dir):
        print(f"No {QPWS_FILE} in {locations_dir}: run `qc qpws-pages --fetch` first.")
        return 1
    with psycopg.connect(psycopg_conninfo()) as conn:
        link_campgrounds(conn, locations_dir)
        for line in qpws_report(conn):
            print(line)
    return 0


def postcodes_command(locations_dir: Path, fetch: bool) -> int:
    path = locations_dir / POSTCODES_FILE
    if fetch:
        locations_dir.mkdir(parents=True, exist_ok=True)
        with httpx.Client(
            headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=60
        ) as client:
            path.write_text(json.dumps(fetch_postcodes(client)), encoding="utf-8")
    if not path.exists():
        print(f"No {POSTCODES_FILE} in {locations_dir}: run `qc postcodes --fetch` first.")
        return 1
    with psycopg.connect(psycopg_conninfo()) as conn:
        n = load_postcodes(conn, path)
    print(f"{n:,} postcode centres (ABS postal areas 2021, © Commonwealth of Australia, CC BY 4.0)")
    return 0


def places_command(locations_dir: Path, fetch: bool) -> int:
    path = locations_dir / PLACES_FILE
    if fetch:
        locations_dir.mkdir(parents=True, exist_ok=True)
        with httpx.Client(
            headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=60
        ) as client:
            path.write_text(json.dumps(fetch_places(client)), encoding="utf-8")
    if not path.exists():
        print(f"No {PLACES_FILE} in {locations_dir}: run `qc places --fetch` first.")
        return 1
    with psycopg.connect(psycopg_conninfo()) as conn:
        n = load_places(conn, path)
    print(f"{n:,} Queensland places (ABS ASGS 2021, © Commonwealth of Australia, CC BY 4.0)")
    return 0


def fetch_locations(locations_dir: Path) -> None:
    locations_dir.mkdir(parents=True, exist_ok=True)
    with httpx.Client(
        headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=60
    ) as client:
        camps = fetch_osm_camp_sites(client)
        (locations_dir / OSM_FILE).write_text(json.dumps(camps), encoding="utf-8")
        print(f"{len(camps['elements'])} OSM campsites (© OpenStreetMap contributors, ODbL)")
        parks = fetch_park_outlines(client)
        (locations_dir / PARKS_FILE).write_text(json.dumps(parks), encoding="utf-8")
        print(f"{len(parks['features'])} park outlines (© State of Queensland, CC BY 4.0)")


def locations_command(locations_dir: Path, fetch: bool, sample: int) -> int:
    if fetch:
        fetch_locations(locations_dir)
    if not has_sources(locations_dir):
        print(f"No location files in {locations_dir}: run `qc locations --fetch` first.")
        return 1
    with psycopg.connect(psycopg_conninfo()) as conn:
        for line in refresh_locations(conn, locations_dir):
            print(line)
        for line in location_report(conn, sample):
            print(line)
    return 0


def download_all(
    client: httpx.Client, urls: Sequence[str], dest_dir: Path, pause: float = 0.0
) -> list[str]:
    """Download every URL, carrying on past failures. Returns one message per failure."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    downloaded = cached = 0

    for url in urls:
        already_there = set(dest_dir.iterdir())
        try:
            path = download_with_retry(client, url, dest_dir)
        except httpx.HTTPError as exc:
            failures.append(f"{url}: {exc}")
            print(f"  failed  {url}: {exc}")
            continue
        if path in already_there:
            cached += 1
        else:
            downloaded += 1
            print(f"  fetched {path.name}")
            time.sleep(pause)

    print(f"{downloaded} downloaded, {cached} already cached, {len(failures)} failed")
    return failures


def download_command(data_dir: Path) -> int:
    with httpx.Client(
        headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=60
    ) as client:
        urls = camping_csv_urls(fetch_package(client))
        print(f"{len(urls)} camping CSVs listed, saving to {data_dir}")
        failures = download_all(client, urls, data_dir, pause=PAUSE_BETWEEN_DOWNLOADS)
    return 1 if failures else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="qc", description="Quiet Camps data tools.")
    commands = parser.add_subparsers(dest="command", required=True)

    download = commands.add_parser(
        "download",
        help="Fetch every camping-permit CSV from data.qld.gov.au.",
        description=(
            "Fetch every camping-permit CSV from data.qld.gov.au (CC BY 4.0). "
            "Files already on disk are never fetched again: delete one to refresh it."
        ),
    )
    download.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)

    profile_parser = commands.add_parser(
        "profile", help="Report header layouts, encodings and value formats of the CSVs."
    )
    profile_parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)

    quality_parser = commands.add_parser(
        "quality", help="Parse every CSV and report nights, repeats and missing values per file."
    )
    quality_parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)

    load_parser = commands.add_parser(
        "load",
        help="Load every CSV into Postgres.",
        description=(
            "Load every CSV into Postgres, one transaction per file. A file's old rows are "
            "replaced, so running it again changes nothing."
        ),
    )
    load_parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)

    commands.add_parser(
        "refresh",
        help="Rebuild campgrounds, the calendar and the views (qc load does this too).",
        description=(
            "Rebuild what's derived from the loaded nights: campgrounds (after editing "
            "campground_merges.csv), the calendar of holiday nights, area_night, "
            "campground_typical and, once downloaded, the locations."
        ),
    )
    commands.add_parser(
        "campgrounds",
        help="List likely typos among campground names, as rows for campground_merges.csv.",
    )

    locations = commands.add_parser(
        "locations",
        help="Locate campgrounds from OSM campsites and park outlines, and list what needs a look.",
        description=(
            "Match every campground to an OpenStreetMap campsite (ODbL) inside its park "
            "(Queensland protected areas, CC BY 4.0), or fall back to the park's centre. "
            "Reviewed fixes go in location_overrides.csv. qc load and qc refresh re-run "
            "the matching from the downloaded files."
        ),
    )
    locations.add_argument(
        "--fetch", action="store_true", help="Download the OSM campsites and park outlines first."
    )
    locations.add_argument(
        "--sample", type=int, default=0, metavar="N", help="Also list N clean matches to check."
    )
    locations.add_argument("--locations-dir", type=Path, default=DEFAULT_LOCATIONS_DIR)

    postcodes = commands.add_parser(
        "postcodes",
        help="Load the centre of every postcode, for where campers come from.",
        description=(
            "Load the centre of every ABS postal area (ASGS 2021, CC BY 4.0) into "
            "postcode_centroid. PO-box-only postcodes have no area, so no centre."
        ),
    )
    postcodes.add_argument(
        "--fetch", action="store_true", help="Download the postal area centres first."
    )
    postcodes.add_argument("--locations-dir", type=Path, default=DEFAULT_LOCATIONS_DIR)

    places = commands.add_parser(
        "places",
        help="Load Queensland's suburbs, towns and council areas, for searching near a place.",
        description=(
            "Load the centre of every Queensland suburb or locality and council area (ABS "
            "ASGS 2021, CC BY 4.0) into place: what 'near Noosa' and 'from Toowoomba' mean."
        ),
    )
    places.add_argument("--fetch", action="store_true", help="Download the places first.")
    places.add_argument("--locations-dir", type=Path, default=DEFAULT_LOCATIONS_DIR)

    qpws = commands.add_parser(
        "qpws-pages",
        help="Link every campground to its QPWS camping area or park page, and list the rest.",
        description=(
            "Match every campground to its camping area's page on parks.qld.gov.au, or its "
            "park's page, from QPWS's two A to Z listings. qc load and qc refresh re-run the "
            "matching from the downloaded file."
        ),
    )
    qpws.add_argument(
        "--fetch",
        action="store_true",
        help=(
            "Download the listings first, from their latest captures on the Internet Archive "
            "(parks.qld.gov.au turns scripts away)."
        ),
    )
    qpws.add_argument("--locations-dir", type=Path, default=DEFAULT_LOCATIONS_DIR)

    openapi = commands.add_parser(
        "openapi",
        help="Write the API's OpenAPI document, for the web client's generated types.",
        description=(
            "Write api/openapi.json from the app. Commit it, then run `pnpm api:types` in web/: "
            "a test fails while the committed file differs from the app."
        ),
    )
    openapi.add_argument("--output", type=Path, default=OPENAPI_FILE)

    args = parser.parse_args(argv)
    match args.command:
        case "download":
            return download_command(args.data_dir)
        case "profile":
            for line in profile(args.data_dir):
                print(line, flush=True)
            return 0
        case "quality":
            for line in quality(args.data_dir):
                print(line, flush=True)
            return 0
        case "load":
            with psycopg.connect(psycopg_conninfo()) as conn:
                for line in load_all(conn, args.data_dir):
                    print(line, flush=True)
                for line in refresh_locations(conn, DEFAULT_LOCATIONS_DIR):
                    print(line, flush=True)
            return 0
        case "refresh":
            with psycopg.connect(psycopg_conninfo()) as conn:
                for line in refresh_derived(conn):
                    print(line, flush=True)
                for line in refresh_locations(conn, DEFAULT_LOCATIONS_DIR):
                    print(line, flush=True)
            return 0
        case "locations":
            return locations_command(args.locations_dir, args.fetch, args.sample)
        case "postcodes":
            return postcodes_command(args.locations_dir, args.fetch)
        case "places":
            return places_command(args.locations_dir, args.fetch)
        case "qpws-pages":
            return qpws_pages_command(args.locations_dir, args.fetch)
        case "openapi":
            args.output.write_text(openapi_document())
            print(f"wrote {args.output}")
            return 0
        case "campgrounds":
            with psycopg.connect(psycopg_conninfo()) as conn:
                for line in campground_suggestions(conn):
                    print(line)
            return 0
        case _:
            parser.error(f"unknown command {args.command}")
