from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

from quiet_camps.ingest.download import download_csv

URL = "https://data.example.org/__data/assets/file/0025/443644/qpws-permits-camping-jul26-sep26.csv"
CSV = b"Type,Postcode,State\nCamping,4000,QLD\n"


def client_for(transport: httpx.MockTransport) -> httpx.Client:
    return httpx.Client(transport=transport)


def test_downloads_into_dest_dir_named_after_the_url(tmp_path: Path) -> None:
    with client_for(httpx.MockTransport(lambda request: httpx.Response(200, content=CSV))) as c:
        path = download_csv(c, URL, tmp_path)

    assert path == tmp_path / "qpws-permits-camping-jul26-sep26.csv"
    assert path.read_bytes() == CSV


def test_query_string_is_not_part_of_the_file_name(tmp_path: Path) -> None:
    with client_for(httpx.MockTransport(lambda request: httpx.Response(200, content=CSV))) as c:
        path = download_csv(c, f"{URL}?v=2", tmp_path)

    assert path.name == "qpws-permits-camping-jul26-sep26.csv"


def test_skips_the_request_when_the_file_is_already_there(tmp_path: Path) -> None:
    cached = tmp_path / "qpws-permits-camping-jul26-sep26.csv"
    cached.write_bytes(b"cached")

    def fail(request: httpx.Request) -> httpx.Response:
        pytest.fail(f"unexpected request to {request.url}")

    with client_for(httpx.MockTransport(fail)) as c:
        path = download_csv(c, URL, tmp_path)

    assert path == cached
    assert path.read_bytes() == b"cached"


@pytest.fixture
def dest_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # Run from tmp_path too, so a stray file in the working directory is caught.
    monkeypatch.chdir(tmp_path)
    dest = tmp_path / "raw"
    dest.mkdir()
    return dest


def test_http_error_raises_and_leaves_no_file(tmp_path: Path, dest_dir: Path) -> None:
    with (
        client_for(httpx.MockTransport(lambda request: httpx.Response(404))) as c,
        pytest.raises(httpx.HTTPStatusError),
    ):
        download_csv(c, URL, dest_dir)

    assert list(tmp_path.rglob("*")) == [dest_dir]


def test_connection_drop_mid_download_leaves_no_partial_file(
    tmp_path: Path, dest_dir: Path
) -> None:
    def chunks() -> Iterator[bytes]:
        yield b"Type,Postcode,State\n"
        raise httpx.ReadError("connection reset")

    with (
        client_for(httpx.MockTransport(lambda request: httpx.Response(200, content=chunks()))) as c,
        pytest.raises(httpx.ReadError),
    ):
        download_csv(c, URL, dest_dir)

    # A half-written CSV must not be mistaken for a cached one on the next run.
    assert list(tmp_path.rglob("*")) == [dest_dir]
