from pathlib import Path

import pytest

from quiet_camps.ingest.campgrounds import Key, area_key
from quiet_camps.ingest.geo import Polygon, bbox
from quiet_camps.ingest.locations import (
    Flag,
    Location,
    OsmCamp,
    Override,
    ParkOutline,
    Source,
    has_place_name,
    load_overrides,
    locate,
    match_key,
    name_score,
    osm_camps,
    park_outlines,
)

# Main Range, a square about 11 km across with its centre at (-28.0, 152.4).
CENTRE = (-28.0, 152.4)


def square(lat: float, lon: float, half: float) -> Polygon:
    ring = [
        [lon - half, lat - half],
        [lon + half, lat - half],
        [lon + half, lat + half],
        [lon - half, lat + half],
        [lon - half, lat - half],
    ]
    return {"type": "Polygon", "coordinates": [ring]}


def outline(name: str, key: str, lat: float, lon: float, half: float = 0.05) -> ParkOutline:
    geometry = square(lat, lon, half)
    return ParkOutline(len(name), name, key, "NP", 1000.0, (lat, lon), geometry, bbox(geometry))


MAIN_RANGE = outline("Main Range National Park", "main range", *CENTRE)

_next_id = iter(range(1, 1000))


def camp(name: str, lat: float, lon: float, *, business: bool = False) -> OsmCamp:
    return OsmCamp("node", next(_next_id), name, match_key(name), (lat, lon), None, business)


def locate_one(
    area: str,
    camps: list[OsmCamp],
    outlines: list[ParkOutline] | None = None,
    overrides: dict[Key, Override] | None = None,
    park: str = "main range",
) -> Location:
    """Locate one campground; an anchor elsewhere in the park pins the park centre.

    Keys as the campground table stores them (area_key), not as OSM names (match_key).
    """
    anchor = camp("Anchor Unique Camp", -28.01, 152.41)
    found = locate(
        [(1, (park, area_key(area))), (2, (park, "anchor unique"))],
        [*camps, anchor],
        [MAIN_RANGE] if outlines is None else outlines,
        overrides,
    )
    return found[0]


@pytest.mark.parametrize(
    ("name", "key"),
    [
        ("Spicer's Gap Campground - Main Range NP", "spicers gap"),
        ("Fern Flat Bush Camp", "fern flat"),
        ("Freshwater Camping & Day Use Area", "freshwater"),
        ("Booloumba Creek No 4 Campground", "booloumba creek 4"),
    ],
)
def test_match_key_drops_what_isnt_the_place(name: str, key: str) -> None:
    assert match_key(name) == key


def test_a_number_alone_is_not_a_place_name() -> None:
    assert not has_place_name("1")
    assert not has_place_name("the 1")
    assert has_place_name("palms")


def test_name_score_never_matches_across_a_number_or_a_compass_word() -> None:
    assert name_score("noosa river 1", "noosa river 13") == 0
    assert name_score("north kobble", "south kobble") == 0
    assert name_score("1", "1") == 0  # "Camping area 1" and "Camp 1": no place name at all
    assert name_score("the haven scraggy point", "the haven") == 100


def test_an_exact_match_inside_the_park_is_clean() -> None:
    loc = locate_one("Poplar Flat camping area", [camp("Poplar Flat Campground", -28.0, 152.4)])
    assert loc.source is Source.OSM
    assert loc.flags == frozenset()
    assert loc.at == (-28.0, 152.4)
    assert loc.park == MAIN_RANGE


def test_a_match_that_contains_more_words_is_flagged() -> None:
    loc = locate_one("Poplar Flat camping area", [camp("Poplar Flat Hollow", -28.0, 152.4)])
    assert loc.source is Source.OSM
    assert loc.flags == {Flag.CONTAINS}


def test_a_near_miss_spelling_is_flagged_weak() -> None:
    loc = locate_one("Governors Waterhole camping area", [camp("Goveners Waterhole", -28.0, 152.4)])
    assert loc.source is Source.OSM
    assert loc.flags == {Flag.WEAK_NAME}


def test_no_match_falls_back_to_the_park_centre_from_its_anchors() -> None:
    loc = locate_one("Poplar Flat camping area", [camp("Somewhere Else", -28.0, 152.4)])
    assert loc.source is Source.PARK_OSM
    assert loc.at == (-28.01, 152.41)  # the only anchor
    assert loc.camp is None


def test_a_park_without_anchors_uses_its_official_centre() -> None:
    found = locate([(1, ("main range", "poplar flat"))], [], [MAIN_RANGE])
    assert found[0].source is Source.PARK_QLD
    assert found[0].at == CENTRE


def test_a_match_beyond_the_radius_is_ignored() -> None:
    # 1° north is about 111 km from the park.
    loc = locate_one("Poplar Flat camping area", [camp("Poplar Flat Campground", -27.0, 152.4)])
    assert loc.source is Source.PARK_OSM
    assert loc.camp is None


def test_a_match_outside_its_park_is_rejected() -> None:
    # 0.07° east of the centre: about 2 km outside the square, well inside the radius.
    stinson = camp("Stinson Memorial Park", -28.0, 152.47)
    loc = locate_one("Stinson remote bush camp", [stinson])
    assert loc.source is Source.PARK_OSM
    assert Flag.REJECTED_OSM in loc.flags
    assert loc.camp == stinson  # kept, so the review list can show what was rejected


def test_a_match_just_outside_its_park_is_kept_and_flagged() -> None:
    # 0.055° east: about 0.5 km outside, like a beach camp on the boundary.
    loc = locate_one("Poplar Flat camping area", [camp("Poplar Flat Campground", -28.0, 152.455)])
    assert loc.source is Source.OSM
    assert loc.flags == {Flag.EDGE_OF_PARK}


def test_a_business_is_rejected_however_good_the_name() -> None:
    roadhouse = camp("Poplar Flat Roadhouse", -28.0, 152.4, business=True)
    loc = locate_one("Poplar Flat camping area", [roadhouse])
    assert loc.source is Source.PARK_OSM
    assert Flag.REJECTED_OSM in loc.flags


def test_two_equal_matches_far_apart_are_a_tie_and_rejected() -> None:
    a = camp("Neurum Creek Campground", -28.0, 152.38)
    b = camp("Neurum Creek Campground", -28.0, 152.43)  # about 5 km east
    loc = locate_one("Neurum Creek camping area", [a, b])
    assert loc.source is Source.PARK_OSM
    assert {Flag.TIE, Flag.REJECTED_OSM} <= loc.flags


def test_a_business_with_the_same_name_does_not_make_a_tie() -> None:
    campground = camp("Neurum Creek Campground", -28.0, 152.38)
    retreat = camp("Neurum Creek Bush Retreat", -28.0, 152.43, business=True)
    loc = locate_one("Neurum Creek camping area", [retreat, campground])
    assert loc.source is Source.OSM
    assert loc.camp == campground


def test_the_same_words_beat_a_longer_name_that_contains_them() -> None:
    falls = camp("Alligator Creek Falls camping area", -28.0, 152.38)
    creek = camp("Alligator Creek Campground", -28.0, 152.43)
    loc = locate_one("Alligator Creek camping area", [falls, creek])
    assert loc.source is Source.OSM
    assert loc.camp == creek
    assert loc.flags == frozenset()


def test_two_equal_matches_close_together_are_one_place() -> None:
    a = camp("Ungowa", -28.0, 152.4)
    b = camp("Ungowa", -28.0, 152.402)  # about 200 m apart
    loc = locate_one("Ungowa camping area", [a, b])
    assert loc.source is Source.OSM
    assert loc.flags == frozenset()


def test_a_park_with_no_outline_is_located_by_anchors_and_flagged() -> None:
    loc = locate_one(
        "Central Station camping area",
        [camp("Central Station Campground", -28.0, 152.4)],
        outlines=[],
        park="kgari",
    )
    assert loc.source is Source.OSM
    assert loc.flags == {Flag.NO_PARK_OUTLINE}


def test_an_anchor_extends_the_park_to_the_outline_it_lies_in() -> None:
    # K'gari Recreation Area has no outline of its own; its campgrounds are in Great Sandy NP.
    great_sandy = outline("Great Sandy National Park", "great sandy", *CENTRE)
    loc = locate_one(
        "Central Station camping area",
        [camp("Central Station Campground", -28.0, 152.4)],
        outlines=[great_sandy],
        park="kgari",
    )
    assert loc.source is Source.OSM
    assert loc.flags == frozenset()
    assert loc.park == great_sandy


def test_campgrounds_sharing_one_osm_point_are_flagged() -> None:
    speewah = camp("Speewah Campground", -28.0, 152.4)
    found = locate(
        [(1, ("main range", "speewah tent only")), (2, ("main range", "speewah multi use"))],
        [speewah],
        [MAIN_RANGE],
    )
    assert [loc.source for loc in found] == [Source.OSM, Source.OSM]
    assert all(Flag.SHARED_POINT in loc.flags for loc in found)


def test_overrides_pick_a_campsite_set_coordinates_or_reject() -> None:
    a = camp("Neurum Creek Campground", -28.0, 152.38)
    b = camp("Neurum Creek Campground", -28.0, 152.43)
    picked = locate_one(
        "Neurum Creek camping area",
        [a, b],
        overrides={("main range", "neurum creek"): Override(("node", b.osm_id), None)},
    )
    assert (picked.source, picked.at, picked.flags) == (Source.OSM, b.at, {Flag.REVIEWED})

    manual = locate_one(
        "Neurum Creek camping area",
        [a],
        overrides={("main range", "neurum creek"): Override(None, (-28.02, 152.39))},
    )
    assert (manual.source, manual.at) == (Source.MANUAL, (-28.02, 152.39))

    rejected = locate_one(
        "Neurum Creek camping area",
        [a],
        overrides={("main range", "neurum creek"): Override(None, None)},
    )
    assert rejected.source is Source.PARK_OSM
    assert rejected.flags == {Flag.REVIEWED, Flag.REJECTED_OSM}


def test_load_overrides_reads_all_three_kinds(tmp_path: Path) -> None:
    path = tmp_path / "overrides.csv"
    path.write_text(
        "park,area,osm,lat,lon,note\n"
        "main range,a,node/42,,,picked\n"
        "main range,b,,-28.1,152.3,manual\n"
        "main range,c,,,,rejected\n",
        encoding="utf-8",
    )
    assert load_overrides(path) == {
        ("main range", "a"): Override(("node", 42), None),
        ("main range", "b"): Override(None, (-28.1, 152.3)),
        ("main range", "c"): Override(None, None),
    }


def test_the_committed_overrides_parse() -> None:
    assert all(isinstance(o, Override) for o in load_overrides().values())


def test_osm_camps_reads_nodes_ways_and_relations() -> None:
    way_ring = [
        {"lat": -28.0, "lon": 152.0},
        {"lat": -28.0, "lon": 152.002},
        {"lat": -28.002, "lon": 152.002},
        {"lat": -28.0, "lon": 152.0},
    ]
    overpass = {
        "elements": [
            {"type": "node", "id": 1, "lat": -28.1, "lon": 152.1, "tags": {"name": "Rum Jungle"}},
            {
                "type": "way",
                "id": 2,
                "bounds": {"minlat": -28.002, "minlon": 152.0, "maxlat": -28.0, "maxlon": 152.002},
                "geometry": way_ring,
                "tags": {"name": "Charlie Moreland Campground"},
            },
            {
                "type": "relation",
                "id": 3,
                "bounds": {"minlat": -27.0, "minlon": 151.0, "maxlat": -26.0, "maxlon": 152.0},
                "tags": {"name": "Hebel Caravan Park"},
            },
            {"type": "node", "id": 4, "lat": -28.1, "lon": 152.1, "tags": {"amenity": "toilets"}},
            {
                "type": "node",
                "id": 5,
                "lat": -28.1,
                "lon": 152.1,
                "tags": {"name": "Private Paddock", "access": "private"},
            },
        ]
    }
    camps = osm_camps(overpass)
    assert [(c.osm_type, c.osm_id, c.key) for c in camps] == [
        ("node", 1, "rum jungle"),
        ("way", 2, "charlie moreland"),
        ("relation", 3, "hebel caravan park"),
        ("node", 5, "private paddock"),
    ]
    assert camps[1].at == pytest.approx((-28.001, 152.001))
    assert camps[1].outline == {
        "type": "Polygon",
        "coordinates": [[[152.0, -28.0], [152.002, -28.0], [152.002, -28.002], [152.0, -28.0]]],
    }
    assert camps[2].at == (-26.5, 151.5)
    assert camps[2].outline is None
    assert [c.business for c in camps] == [False, False, True, True]


def test_park_outlines_reads_the_qld_geojson() -> None:
    geometry = square(-20.08, 148.51, 0.05)
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "objectid": 412,
                    "estatename": "Gloucester Island National Park",
                    "esttype": "NP",
                    "latitude": -20.08,
                    "longitude": 148.51,
                    "gazareaha": 2977.755,
                },
                "geometry": geometry,
            }
        ],
    }
    [park] = park_outlines(geojson)
    assert (park.id, park.key) == (412, "gloucester islands")  # the permits' name for it
    assert (park.kind, park.area_ha, park.centre) == ("NP", 2977.755, (-20.08, 148.51))
    assert park.bbox == pytest.approx((148.46, -20.13, 148.56, -20.03))
