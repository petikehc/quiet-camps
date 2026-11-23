import json
from pathlib import Path
from typing import Any

import httpx
import psycopg
import pytest
from psycopg.rows import TupleRow

from quiet_camps.cli import fetch_postcodes, main
from quiet_camps.db.postcodes import POSTCODES_FILE, load_postcodes
from quiet_camps.ingest.postcodes import PostcodeCentroid, postcode_centroids


def feature(code: str, coordinates: list[list[float]] | None) -> dict[str, Any]:
    geometry = {"type": "MultiPoint", "coordinates": coordinates} if coordinates else None
    return {"type": "Feature", "geometry": geometry, "properties": {"poa_code_2021": code}}


BRISBANE = feature("4000", [[153.0212, -27.4653]])
DARWIN = feature("0800", [[130.8418, -12.4604]])  # NT codes keep their leading zero


def collection(*features: dict[str, Any]) -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": list(features)}


def test_postcode_centroids_reads_lat_and_lon() -> None:
    assert postcode_centroids(collection(BRISBANE, DARWIN)) == [
        PostcodeCentroid(postcode="4000", lat=-27.4653, lon=153.0212),
        PostcodeCentroid(postcode="0800", lat=-12.4604, lon=130.8418),
    ]


@pytest.mark.parametrize(
    "odd",
    [
        feature("9494", None),  # no geometry
        feature("9797", []),  # an empty MultiPoint
        feature("NOUSUAL", [[150.0, -30.0]]),  # not a postcode
    ],
)
def test_postcode_centroids_skips_areas_without_a_place(odd: dict[str, Any]) -> None:
    assert postcode_centroids(collection(BRISBANE, odd)) == [
        PostcodeCentroid(postcode="4000", lat=-27.4653, lon=153.0212)
    ]


def test_fetch_postcodes_pages_until_a_short_page(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("quiet_camps.cli.ABS_PAGE", 2)
    offsets: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        offset = request.url.params["resultOffset"]
        offsets.append(offset)
        pages = {"0": [BRISBANE, DARWIN], "2": [BRISBANE]}
        return httpx.Response(200, json=collection(*pages[offset]))

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetched = fetch_postcodes(client)

    assert offsets == ["0", "2"]
    assert len(fetched["features"]) == 3


def test_load_postcodes_replaces_the_table(
    conn: psycopg.Connection[TupleRow], tmp_path: Path
) -> None:
    path = tmp_path / POSTCODES_FILE
    path.write_text(json.dumps(collection(BRISBANE, DARWIN)), encoding="utf-8")
    load_postcodes(conn, path)
    path.write_text(json.dumps(collection(DARWIN)), encoding="utf-8")

    assert load_postcodes(conn, path) == 1

    rows = conn.execute("SELECT postcode, lat, lon FROM postcode_centroid").fetchall()
    assert rows == [("0800", -12.4604, 130.8418)]


def test_qc_postcodes_without_a_file_says_how_to_fetch(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["postcodes", "--locations-dir", str(tmp_path)]) == 1
    assert "qc postcodes --fetch" in capsys.readouterr().out
