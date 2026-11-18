from pathlib import Path

import httpx
import pytest

from quiet_camps.cli import download_all, fetch_package, is_transient

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
