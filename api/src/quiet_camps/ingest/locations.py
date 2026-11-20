"""Where each campground is: an OpenStreetMap campsite where one matches, else its park.

The permit data has no coordinates. OSM has most campsites, as volunteers named them, and the
Queensland Government publishes park outlines. Names alone mislead ("Stinson remote bush camp"
is not "Stinson Memorial Park", 2 km outside Lamington), so a match must also lie in its park.

1. Anchors: campgrounds whose name has exactly one strong OSM match in all of Queensland.
   They locate their park, which works for parks with no outline (K'gari Recreation Area).
2. The rest match within RADIUS_KM of their park's centre.
3. A match more than EDGE_KM outside the park, at a business, or tied with another place is
   rejected, and the campground falls back to its park centre.
4. Anything not straightforward gets a flag, so a map or list can show it.

Reviewed fixes go in location_overrides.csv. See docs/adr/0003.
"""

import csv
import re
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

from quiet_camps.ingest.campgrounds import DISTINGUISHING, Key, area_key, park_key
from quiet_camps.ingest.geo import (
    BBox,
    Geometry,
    LatLon,
    Polygon,
    bbox,
    contains,
    km,
    km_outside,
)

OVERRIDES_CSV = Path(__file__).with_name("location_overrides.csv")

MATCH_SCORE = 85  # lowest name score that counts as a match
ANCHOR_SCORE = 95  # an anchor needs a near-exact name
RADIUS_KM = 50  # how far from its park's centre a campground's match may be
EDGE_KM = 1  # outlines are simplified to ~100 m, and beach camps sit on the boundary
TIE_KM = 1  # two equal matches closer than this are one place mapped twice

# What OSM names add that isn't the place: "Fern Flat Bush Camp", "Freshwater Camping & Day
# Use Area", "Booloumba Creek No 4 Campground". On top of the campground rules' AREA_WORDS.
EXTRA_WORDS = re.compile(r"\b(bush|walkers?|great walk|day use|no)\b|&")
# Not a QPWS campground, however good the name match: "Simpson Desert Oasis Roadhouse".
BUSINESS = re.compile(
    r"roadhouse|retreat|caravan|holiday (park|village)|tourist park|showground|hotel|motel"
    r"|resort|cabins|\bfarm\b|station stay",
    re.IGNORECASE,
)
# Outline names whose key differs from the permits' park key.
OUTLINE_ALIASES = {"gloucester island": "gloucester islands"}


class Source(StrEnum):
    OSM = "osm"  # an OSM campsite
    PARK_OSM = "park_osm"  # the middle of the park's anchors (so also from OSM)
    PARK_QLD = "park_qld"  # the official centre of the park
    MANUAL = "manual"  # coordinates from location_overrides.csv


class Flag(StrEnum):
    WEAK_NAME = "weak_name"  # name score below 100
    CONTAINS = "contains"  # one name only contains the other: "The Haven (Scraggy Point)"
    TIE = "tie"  # equally good OSM matches more than TIE_KM apart
    SHARED_POINT = "shared_point"  # another campground matched the same OSM campsite
    EDGE_OF_PARK = "edge_of_park"  # up to EDGE_KM outside its park
    NO_PARK_OUTLINE = "no_park_outline"  # nothing to check the point against
    REJECTED_OSM = "rejected_osm"  # had an OSM match that failed a check: see osm_name
    REVIEWED = "reviewed"  # set by location_overrides.csv


@dataclass(frozen=True)
class OsmCamp:
    osm_type: str  # node, way or relation
    osm_id: int
    name: str
    key: str
    at: LatLon
    outline: Polygon | None  # for campsites drawn as an area
    business: bool


@dataclass(frozen=True)
class ParkOutline:
    id: int  # the service's objectid
    name: str
    key: str
    kind: str  # NP, CP, SF...
    area_ha: float
    centre: LatLon
    geometry: Geometry
    bbox: BBox


@dataclass(frozen=True)
class Override:
    osm: tuple[str, int] | None  # pick this OSM campsite
    at: LatLon | None  # or put it here
    # Neither: reject the OSM match and use the park centre.


@dataclass(frozen=True)
class Location:
    campground_id: int
    at: LatLon | None
    source: Source | None
    flags: frozenset[Flag]
    camp: OsmCamp | None  # the match, or the rejected one
    score: float | None
    park: ParkOutline | None  # the outline to draw with it


@dataclass
class _Candidate:
    score: float
    camp: OsmCamp


def match_key(name: str) -> str:
    """'Spicer's Gap Campground - Main Range NP' → 'spicers gap'."""
    return _drop_extra_words(area_key(name.split(" - ")[0]))


def _drop_extra_words(key: str) -> str:
    """A campground's area key, compared like an OSM name: 'stinson bush' → 'stinson'."""
    return " ".join(EXTRA_WORDS.sub(" ", key).split())


def has_place_name(key: str) -> bool:
    """'camp 1' → '1' names no place, and would match every 'Camp 1' in Queensland."""
    words = DISTINGUISHING.sub(" ", key).split()
    return any(len(w) >= 3 and w != "the" for w in words)


def name_score(ours: str, theirs: str) -> float:
    """0 to 100, word-based, so 'the haven scraggy point' matches 'the haven' (flagged CONTAINS)."""
    if not (has_place_name(ours) and has_place_name(theirs)):
        return 0
    if _markers(ours) != _markers(theirs):  # "noosa river 1" is not "noosa river 13"
        return 0
    if min(len(ours), len(theirs)) < 6:
        return fuzz.ratio(ours, theirs)
    return max(fuzz.ratio(ours, theirs), fuzz.token_set_ratio(ours, theirs))


def _markers(key: str) -> set[str]:
    return {m.group(0) for m in DISTINGUISHING.finditer(key)}


def osm_camps(overpass: dict[str, Any]) -> list[OsmCamp]:
    """Named campsites from an Overpass `out geom` response."""
    camps: list[OsmCamp] = []
    for element in overpass["elements"]:
        tags: dict[str, str] = element.get("tags", {})
        name = tags.get("name")
        if not name:
            continue
        outline: Polygon | None = None
        if element["type"] == "node":
            at = (element["lat"], element["lon"])
        else:
            b = element["bounds"]
            at = ((b["minlat"] + b["maxlat"]) / 2, (b["minlon"] + b["maxlon"]) / 2)
            points = element.get("geometry", [])
            if element["type"] == "way" and len(points) >= 4 and points[0] == points[-1]:
                ring = [[p["lon"], p["lat"]] for p in points]
                outline = {"type": "Polygon", "coordinates": [ring]}
        camps.append(
            OsmCamp(
                osm_type=element["type"],
                osm_id=element["id"],
                name=name,
                key=match_key(name),
                at=at,
                outline=outline,
                business=bool(BUSINESS.search(name)) or tags.get("access") == "private",
            )
        )
    return camps


def park_outlines(geojson: dict[str, Any]) -> list[ParkOutline]:
    """Outlines from the Queensland protected areas service (GeoJSON, EPSG:4326)."""
    outlines: list[ParkOutline] = []
    for feature in geojson["features"]:
        props = feature["properties"]
        geometry: Geometry = feature["geometry"]
        key = park_key(props["estatename"])
        outlines.append(
            ParkOutline(
                id=props["objectid"],
                name=props["estatename"],
                key=OUTLINE_ALIASES.get(key, key),
                kind=props["esttype"],
                area_ha=props["gazareaha"] or 0.0,
                centre=(props["latitude"], props["longitude"]),
                geometry=geometry,
                bbox=bbox(geometry),
            )
        )
    return outlines


def load_overrides(path: Path = OVERRIDES_CSV) -> dict[Key, Override]:
    """{(park, area): Override}. Columns: park,area,osm,lat,lon,note (osm like 'node/123')."""
    overrides: dict[Key, Override] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            osm = None
            if row["osm"]:
                osm_type, osm_id = row["osm"].split("/")
                osm = (osm_type, int(osm_id))
            at = (float(row["lat"]), float(row["lon"])) if row["lat"] else None
            overrides[(row["park"], row["area"])] = Override(osm, at)
    return overrides


@dataclass(frozen=True)
class _Park:
    outlines: list[ParkOutline]  # the outlines its campgrounds may lie in
    centre: tuple[LatLon, Source] | None


def locate(
    campgrounds: Sequence[tuple[int, Key]],
    camps: Sequence[OsmCamp],
    outlines: Sequence[ParkOutline],
    overrides: dict[Key, Override] | None = None,
) -> list[Location]:
    """A location for every campground: (id, (park key, area key)) → Location."""
    if overrides is None:
        overrides = {}
    areas = {cid: _drop_extra_words(area) for cid, (_, area) in campgrounds}
    # Every OSM campsite that could be each campground, anywhere in Queensland.
    candidates = {
        cid: [
            _Candidate(s, camp)
            for camp in camps
            if (s := name_score(areas[cid], camp.key)) >= MATCH_SCORE
        ]
        for cid, _ in campgrounds
    }

    anchors: dict[str, list[LatLon]] = defaultdict(list)
    for cid, (park, _) in campgrounds:
        found = candidates[cid]
        if (
            len(found) == 1
            and fuzz.ratio(areas[cid], found[0].camp.key) >= ANCHOR_SCORE
            and not found[0].camp.business
        ):
            anchors[park].append(found[0].camp.at)

    parks = {park: _park(park, anchors.get(park, []), outlines) for _, (park, _) in campgrounds}
    camp_by_id = {(c.osm_type, c.osm_id): c for c in camps}
    located = [
        _locate_one(cid, areas[cid], candidates[cid], parks[key[0]], overrides.get(key), camp_by_id)
        for cid, key in campgrounds
    ]
    return _flag_shared_points(located)


def _park(park: str, anchors: list[LatLon], outlines: Sequence[ParkOutline]) -> _Park:
    """Its outlines (same name, or holding an anchor) and its centre (anchors first)."""
    same_name = [o for o in outlines if o.key == park]
    expected = list(same_name)
    for at in anchors:
        expected += [o for o in _containing(outlines, at) if o not in expected]

    centre: tuple[LatLon, Source] | None = None
    if anchors:
        lat = statistics.median(p[0] for p in anchors)
        lon = statistics.median(p[1] for p in anchors)
        centre = ((lat, lon), Source.PARK_OSM)
    elif same_name:
        centre = (max(same_name, key=lambda o: o.area_ha).centre, Source.PARK_QLD)
    return _Park(expected, centre)


def _locate_one(
    cid: int,
    area: str,
    candidates: list[_Candidate],
    park: _Park,
    override: Override | None,
    camp_by_id: dict[tuple[str, int], OsmCamp],
) -> Location:
    flags: set[Flag] = set()
    if not park.outlines:
        flags.add(Flag.NO_PARK_OUTLINE)

    if override is not None:
        flags.add(Flag.REVIEWED)
        if override.osm is not None:
            camp = camp_by_id[override.osm]
            return _at(cid, camp.at, Source.OSM, flags, camp, None, park)
        if override.at is not None:
            return _at(cid, override.at, Source.MANUAL, flags, None, None, park)
        flags.add(Flag.REJECTED_OSM)
        return _park_centre(cid, flags, None, None, park)

    def rank(c: _Candidate) -> tuple[bool, float, bool]:
        """Not a business, then the score, then the same words (beats CONTAINS at 100)."""
        return (not c.camp.business, c.score, fuzz.token_sort_ratio(area, c.camp.key) == 100)

    nearby = sorted(
        (c for c in candidates if park.centre and km(c.camp.at, park.centre[0]) <= RADIUS_KM),
        key=rank,
        reverse=True,
    )
    if not nearby:
        return _park_centre(cid, flags, None, None, park)

    best = nearby[0]
    camp = best.camp
    if best.score < 100:
        flags.add(Flag.WEAK_NAME)
    elif not rank(best)[2]:
        flags.add(Flag.CONTAINS)

    rejected = camp.business
    if any(rank(c) == rank(best) and km(c.camp.at, camp.at) > TIE_KM for c in nearby[1:]):
        flags.add(Flag.TIE)
        rejected = True
    if park.outlines:
        outside = min(km_outside(o.geometry, camp.at) for o in park.outlines)
        if outside > EDGE_KM:
            rejected = True
        elif outside > 0:
            flags.add(Flag.EDGE_OF_PARK)

    if rejected:
        flags.add(Flag.REJECTED_OSM)
        return _park_centre(cid, flags, camp, best.score, park)
    return _at(cid, camp.at, Source.OSM, flags, camp, best.score, park)


def _at(
    cid: int,
    at: LatLon,
    source: Source,
    flags: set[Flag],
    camp: OsmCamp | None,
    score: float | None,
    park: _Park,
) -> Location:
    """A located point, with the expected outline it lies in (or is nearest to)."""
    outline = min(park.outlines, key=lambda o: km_outside(o.geometry, at), default=None)
    return Location(cid, at, source, frozenset(flags), camp, score, outline)


def _park_centre(
    cid: int, flags: set[Flag], camp: OsmCamp | None, score: float | None, park: _Park
) -> Location:
    """Only the park is known: its centre and its biggest outline."""
    outline = max(park.outlines, key=lambda o: o.area_ha, default=None)
    if park.centre is None:
        return Location(cid, None, None, frozenset(flags), camp, score, outline)
    at, source = park.centre
    return Location(cid, at, source, frozenset(flags), camp, score, outline)


def _containing(outlines: Iterable[ParkOutline], at: LatLon) -> list[ParkOutline]:
    lat, lon = at
    return [
        o
        for o in outlines
        if o.bbox.min_lon <= lon <= o.bbox.max_lon
        and o.bbox.min_lat <= lat <= o.bbox.max_lat
        and contains(o.geometry, at)
    ]


def _flag_shared_points(located: list[Location]) -> list[Location]:
    def osm_point(loc: Location) -> tuple[str, int] | None:
        if loc.source is Source.OSM and loc.camp is not None:
            return (loc.camp.osm_type, loc.camp.osm_id)
        return None

    uses = Counter(p for loc in located if (p := osm_point(loc)) is not None)
    return [
        replace(loc, flags=loc.flags | {Flag.SHARED_POINT})
        if (p := osm_point(loc)) is not None and uses[p] > 1
        else loc
        for loc in located
    ]
