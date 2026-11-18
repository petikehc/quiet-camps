import argparse
import time
from collections.abc import Sequence
from pathlib import Path

import httpx

from quiet_camps.ingest.ckan import PackageShowResponse, camping_csv_urls
from quiet_camps.ingest.download import download_csv
from quiet_camps.ingest.profile_report import profile
from quiet_camps.ingest.quality_report import quality
from quiet_camps.ingest.retry import retry

PACKAGE_URL = "https://www.data.qld.gov.au/api/3/action/package_show"
PACKAGE_ID = "camping-and-vehicle-permits"
USER_AGENT = "quiet-camps/0.1 (learning project)"
# src/quiet_camps/cli.py → repo root. Works because uv installs the package in editable mode.
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"
PAUSE_BETWEEN_DOWNLOADS = 0.5


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
        case _:
            parser.error(f"unknown command {args.command}")
