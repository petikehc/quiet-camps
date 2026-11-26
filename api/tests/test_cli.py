from pathlib import Path

import httpx
import psycopg
import pytest
from psycopg.rows import TupleRow

from quiet_camps.api.openapi import openapi_document
from quiet_camps.cli import (
    download_all,
    fetch_latest_capture,
    fetch_package,
    fetch_qpws_pages,
    is_transient,
    main,
)
from quiet_camps.ingest.qpws import CAMPGROUNDS_A_Z, PARKS_A_Z

GOOD = "https://data.example.org/files/qpws-permits-camping-jul26-sep26.csv"
MISSING = "https://data.example.org/files/qpws-permits-camping-gone.csv"


def status_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", GOOD)
    response = httpx.Response(status, request=request)
    return httpx.HTTPStatusError(f"{status}", request=request, response=response)


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (status_error(404), False),
        (status_error(403), False),
        (status_error(429), True),
        (status_error(503), True),
        (httpx.ReadError("connection reset"), True),
        (httpx.ConnectTimeout("timed out"), True),
        (ValueError("not a network problem"), False),
    ],
)
def test_is_transient(exc: Exception, expected: bool) -> None:
    assert is_transient(exc) is expected


def test_download_all_reports_a_404_and_carries_on(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        if str(request.url) == MISSING:
            return httpx.Response(404)
        return httpx.Response(200, content=b"Type\nCamping\n")

    dest = tmp_path / "raw"  # doesn't exist yet: download_all creates it
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        first = download_all(client, [MISSING, GOOD], dest)
        second = download_all(client, [MISSING, GOOD], dest)

    assert len(first) == len(second) == 1
    assert MISSING in first[0]
    assert (dest / "qpws-permits-camping-jul26-sep26.csv").read_bytes() == b"Type\nCamping\n"
    # The 404 is asked for once per run (never retried); the good file only on the first run.
    assert requests == [MISSING, GOOD, MISSING]
    out = capsys.readouterr().out
    assert "1 downloaded, 0 already cached, 1 failed" in out
    assert "0 downloaded, 1 already cached, 1 failed" in out


def test_fetch_package_rejects_an_unsuccessful_response() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"success": False, "error": {}})
    )
    with httpx.Client(transport=transport) as client, pytest.raises(RuntimeError):
        fetch_package(client)


def test_fetch_qpws_pages_reads_each_listings_latest_capture() -> None:
    camping = (
        '<li data-park-id="1"><h3><a href="https://parks.qld.gov.au/parks/amamoor/camping/'
        'amamoor-creek">Amamoor Creek camping area</a><small>Amamoor State Forest</small></h3></li>'
    )
    parks = (
        '<li data-park-id="2"><h3><a href="https://parks.qld.gov.au/parks/girringun">'
        "Girringun National Park</a><small>Region: Townsville</small></h3></li>"
    )
    captures = {CAMPGROUNDS_A_Z: ("20261026034219", camping), PARKS_A_Z: ("20260915045150", parks)}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/cdx/search/cdx":
            timestamp = captures[request.url.params["url"]][0]
            return httpx.Response(200, json=[["timestamp"], [timestamp]])
        timestamp, url = request.url.raw_path.decode().removeprefix("/web/").split("id_/", 1)
        assert captures[url][0] == timestamp
        return httpx.Response(200, text=captures[url][1])

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        pages = fetch_qpws_pages(client)

    assert pages == {
        "camping": {
            "captured": "20261026034219",
            "pages": [
                {
                    "url": "https://parks.qld.gov.au/parks/amamoor/camping/amamoor-creek",
                    "name": "Amamoor Creek camping area",
                    "park_name": "Amamoor State Forest",
                }
            ],
        },
        "parks": {
            "captured": "20260915045150",
            "pages": [
                {
                    "url": "https://parks.qld.gov.au/parks/girringun",
                    "name": "Girringun National Park",
                }
            ],
        },
    }


def test_fetch_latest_capture_fails_when_the_archive_has_none() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=[]))
    with (
        httpx.Client(transport=transport) as client,
        pytest.raises(RuntimeError, match="no capture"),
    ):
        fetch_latest_capture(client, PARKS_A_Z)


def test_qc_load_loads_into_the_database(
    conn: psycopg.Connection[TupleRow], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    header = (
        "Reservation Number,Type,Postcode,State,Booking Date,Start Date,Stay Date,"
        "Park,Facility,Adults,Children,Infants"
    )
    row = (
        "576013,Camping,4507,QLD,1/02/2018,31/03/2018,31/03/2018,"
        "Bribie Island NP,Poverty Creek,2,0,0"
    )
    (tmp_path / "q1.csv").write_text(f"{header}\r\n{row}\r\n", encoding="utf-8")

    # The conn fixture points DATABASE_URL at the migrated test database.
    assert main(["load", "--data-dir", str(tmp_path)]) == 0

    assert "1 nights from 1 files" in capsys.readouterr().out
    assert conn.execute("SELECT count(*) FROM camp_night").fetchone() == (1,)


def test_openapi_writes_the_document(tmp_path: Path) -> None:
    output = tmp_path / "openapi.json"

    assert main(["openapi", "--output", str(output)]) == 0

    assert output.read_text() == openapi_document()
