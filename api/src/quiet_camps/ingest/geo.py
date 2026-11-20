"""Just enough geometry to check a point against a park outline: no GIS library needed.

Coordinates follow GeoJSON: [longitude, latitude]. Points elsewhere are (lat, lon) tuples.
"""

import math
from itertools import pairwise
from typing import Literal, NamedTuple, TypedDict

type LatLon = tuple[float, float]
type Ring = list[list[float]]  # [[lon, lat], ...], first point repeated at the end

EARTH_RADIUS_KM = 6371.0088
KM_PER_DEGREE_LAT = 111.32


class Polygon(TypedDict):
    type: Literal["Polygon"]
    coordinates: list[Ring]  # the outer ring, then any holes


class MultiPolygon(TypedDict):
    type: Literal["MultiPolygon"]
    coordinates: list[list[Ring]]


type Geometry = Polygon | MultiPolygon


class BBox(NamedTuple):
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float


def km(a: LatLon, b: LatLon) -> float:
    """Great-circle distance (haversine)."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


def rings(geometry: Geometry) -> list[Ring]:
    """Every ring, outer and holes, of every part."""
    if geometry["type"] == "Polygon":
        return geometry["coordinates"]
    return [ring for polygon in geometry["coordinates"] for ring in polygon]


def bbox(geometry: Geometry) -> BBox:
    points = [p for ring in rings(geometry) for p in ring]
    lons = [p[0] for p in points]
    lats = [p[1] for p in points]
    return BBox(min(lons), min(lats), max(lons), max(lats))


def contains(geometry: Geometry, point: LatLon) -> bool:
    """Ray casting: a ray from the point crosses the edges an odd number of times if it's inside.

    Counting crossings over all rings at once handles holes and separate parts too.
    """
    lat, lon = point
    inside = False
    for ring in rings(geometry):
        for (x1, y1), (x2, y2) in pairwise(ring):
            if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
                inside = not inside
    return inside


def km_outside(geometry: Geometry, point: LatLon) -> float:
    """0 inside the outline, otherwise the distance to its nearest edge.

    Flattens the earth around the point, which is accurate enough over a few km.
    """
    if contains(geometry, point):
        return 0.0
    lat, lon = point
    x_scale = KM_PER_DEGREE_LAT * math.cos(math.radians(lat))

    def xy(p: list[float]) -> tuple[float, float]:
        return (p[0] - lon) * x_scale, (p[1] - lat) * KM_PER_DEGREE_LAT

    nearest = math.inf
    for ring in rings(geometry):
        for a, b in pairwise(ring):
            nearest = min(nearest, _distance_to_segment(xy(a), xy(b)))
    return nearest


def _distance_to_segment(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distance from the origin to the segment from a to b."""
    (ax, ay), (bx, by) = a, b
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / length2))
    return math.hypot(ax + t * dx, ay + t * dy)
