import json
from pathlib import Path

from quiet_camps.ingest.ckan import CkanResource, PackageShowResponse, camping_csv_urls

FIXTURE = Path(__file__).parent / "fixtures" / "package_show.json"


def make_package(resources: list[CkanResource]) -> PackageShowResponse:
    return {"success": True, "result": {"name": "test", "resources": resources}}


def resource(name: str, fmt: str = "CSV") -> CkanResource:
    return {"id": name, "name": name, "format": fmt, "url": f"https://example.org/{name}.csv"}


def test_real_package_keeps_camping_and_combined_files() -> None:
    package: PackageShowResponse = json.loads(FIXTURE.read_text())

    urls = camping_csv_urls(package)

    # 42 camping-only quarters + 7 early files that mix camping and vehicle rows
    assert len(urls) == 49
    assert urls[0].endswith("qpws-permits-camping-jul26-sep26.csv")
    assert urls[-1].endswith("qpws-permits-jan2011-jul2013.csv")
    assert not any("vehicle" in url for url in urls)


def test_vehicle_match_ignores_case_and_keeps_order() -> None:
    package = make_package(
        [resource("Camping B"), resource("VEHICLE permits"), resource("Camping A")]
    )

    assert camping_csv_urls(package) == [
        "https://example.org/Camping B.csv",
        "https://example.org/Camping A.csv",
    ]


def test_non_csv_resources_are_skipped() -> None:
    package = make_package([resource("Camping data dictionary", fmt="PDF")])

    assert camping_csv_urls(package) == []


def test_format_match_ignores_case_and_spaces() -> None:
    package = make_package([resource("Camping A", fmt=" csv")])

    assert camping_csv_urls(package) == ["https://example.org/Camping A.csv"]


def test_no_resources_gives_empty_list() -> None:
    assert camping_csv_urls(make_package([])) == []
