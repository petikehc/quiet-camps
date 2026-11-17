from typing import TypedDict


class CkanResource(TypedDict):
    id: str
    name: str
    format: str
    url: str


class CkanPackage(TypedDict):
    name: str
    resources: list[CkanResource]


class PackageShowResponse(TypedDict):
    success: bool
    result: CkanPackage


def camping_csv_urls(package: PackageShowResponse) -> list[str]:

    return [
        resource["url"]
        for resource in package["result"]["resources"]
        if resource["format"].strip().casefold() == "csv"
        and "vehicle" not in resource["name"].lower()
    ]
