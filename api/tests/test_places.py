"""ABS places: Queensland's suburbs, towns and council areas, for searching near a place."""

import json
from pathlib import Path
from typing import Any

import httpx
import psycopg
import pytest
from psycopg.rows import TupleRow

from quiet_camps.cli import fetch_places, main
from quiet_camps.db.places import PLACES_FILE, load_places
from quiet_camps.ingest.places import AbsPlace, abs_places


def feature(field: str, name: str, lon: float, lat: float, state: str = "3") -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": {"type": "MultiPoint", "coordinates": [[lon, lat]]},
        "properties": {field: name, "state_code_2021": state},
    }


def collection(*features: dict[str, Any]) -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": list(features)}


NOOSA_HEADS = feature("sal_name_2021", "Noosa Heads", 153.0915, -26.4001)
KINGSTON = feature("sal_name_2021", "Kingston (Qld)", 153.1100, -27.6600)
GILBERTON = feature("sal_name_2021", "Gilberton (Gold Coast - Qld)", 153.2700, -27.8000)
SUNSHINE_COAST = feature("lga_name_2021", "Sunshine Coast (R)", 152.9600, -26.6500)
TWEED = feature("lga_name_2021", "Tweed (A)", 153.4000, -28.3000, state="1")  # NSW


def test_places_are_named_the_way_people_say_them() -> None:
    assert abs_places(collection(KINGSTON, GILBERTON), "sal_name_2021", "locality") == [
        AbsPlace(name="Kingston", kind="locality", lat=-27.66, lon=153.11),
        AbsPlace(name="Gilberton", kind="locality", lat=-27.8, lon=153.27),
    ]
    assert abs_places(collection(SUNSHINE_COAST), "lga_name_2021", "council") == [
        AbsPlace(name="Sunshine Coast", kind="council", lat=-26.65, lon=152.96)
    ]


def test_only_queensland_and_only_places() -> None:
    no_address = feature("lga_name_2021", "No usual address (Qld)", 0, 0)
    found = abs_places(collection(SUNSHINE_COAST, TWEED, no_address), "lga_name_2021", "council")

    assert [p.name for p in found] == ["Sunshine Coast"]


def test_fetch_places_asks_for_queensland_from_both_services() -> None:
    asked: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        asked.append((request.url.path, request.url.params["where"]))
        return httpx.Response(200, json=collection(NOOSA_HEADS))

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetched = fetch_places(client)

    assert [path.split("/")[-4] for path, _ in asked] == ["SAL", "LGA"]
    assert {where for _, where in asked} == {"state_code_2021 = '3'"}
    assert set(fetched) == {"localities", "councils"}


def test_load_places_replaces_the_table(conn: psycopg.Connection[TupleRow], tmp_path: Path) -> None:
    path = tmp_path / PLACES_FILE
    both = {"localities": collection(NOOSA_HEADS), "councils": collection(SUNSHINE_COAST)}
    path.write_text(json.dumps(both), encoding="utf-8")
    load_places(conn, path)
    only = {"localities": collection(), "councils": collection(SUNSHINE_COAST)}
    path.write_text(json.dumps(only), encoding="utf-8")

    assert load_places(conn, path) == 1
    rows = conn.execute("SELECT name, kind FROM place").fetchall()
    assert rows == [("Sunshine Coast", "council")]


def test_qc_places_without_a_file_says_how_to_fetch(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["places", "--locations-dir", str(tmp_path)]) == 1
    assert "qc places --fetch" in capsys.readouterr().out
