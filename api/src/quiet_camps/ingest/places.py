import re
from dataclasses import dataclass
from typing import Any

QUEENSLAND = "3"  # the ABS state code

# "Sunshine Coast (R)", "Noosa (S)", "Brisbane (C)": the ABS adds the council's type.
COUNCIL_TYPE = re.compile(r"\s*\([A-Z]{1,3}\)$")
# "Kingston (Qld)", "Gilberton (Gold Coast - Qld)": the ABS tells same-named localities
# apart by state, and within Queensland by region.
STATE_TAG = re.compile(r"\s*\((?:[^()]* - )?Qld\.?\)$")
# Codes for people with no fixed place, not places.
NOT_A_PLACE = re.compile(r"^(No usual address|Migratory|Unincorporated)", re.IGNORECASE)


@dataclass(frozen=True)
class AbsPlace:
    name: str
    kind: str  # locality or council
    lat: float
    lon: float


def abs_places(geojson: dict[str, Any], name_field: str, kind: str) -> list[AbsPlace]:
    """Queensland's places from an ABS point service (ASGS 2021 SAL_PT or LGA_PT, GeoJSON,
    EPSG:4326), named the way people say them."""
    places: list[AbsPlace] = []
    for feature in geojson["features"]:
        properties = feature["properties"]
        geometry = feature["geometry"]
        name: str = properties[name_field]
        if properties["state_code_2021"] != QUEENSLAND or NOT_A_PLACE.match(name):
            continue
        if not geometry or not geometry["coordinates"]:
            continue
        lon, lat = geometry["coordinates"][0]  # a MultiPoint with one point
        name = STATE_TAG.sub("", COUNCIL_TYPE.sub("", name))
        places.append(AbsPlace(name=name, kind=kind, lat=lat, lon=lon))
    return places
