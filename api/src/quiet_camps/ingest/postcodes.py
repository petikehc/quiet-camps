from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PostcodeCentroid:
    postcode: str
    lat: float
    lon: float


def postcode_centroids(geojson: dict[str, Any]) -> list[PostcodeCentroid]:
    """Centres from the ABS postal areas service (ASGS 2021 POA_PT, GeoJSON, EPSG:4326).

    Each centre is a MultiPoint with one point. Areas with no shape (the ABS's "no usual
    address" codes) have no geometry and are skipped.
    """
    centroids: list[PostcodeCentroid] = []
    for feature in geojson["features"]:
        code: str = feature["properties"]["poa_code_2021"]
        geometry = feature["geometry"]
        if not geometry or not geometry["coordinates"] or not code.isdigit():
            continue
        lon, lat = geometry["coordinates"][0]
        centroids.append(PostcodeCentroid(postcode=code, lat=lat, lon=lon))
    return centroids
