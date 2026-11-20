import pytest

from quiet_camps.ingest.geo import MultiPolygon, Polygon, bbox, contains, km, km_outside

# A square 0.1° on each side near K'gari, with a hole in the middle.
SQUARE: Polygon = {
    "type": "Polygon",
    "coordinates": [
        [[153.0, -25.0], [153.1, -25.0], [153.1, -25.1], [153.0, -25.1], [153.0, -25.0]],
        [[153.04, -25.04], [153.06, -25.04], [153.06, -25.06], [153.04, -25.06], [153.04, -25.04]],
    ],
}
ISLANDS: MultiPolygon = {
    "type": "MultiPolygon",
    "coordinates": [
        [[[150.0, -20.0], [150.1, -20.0], [150.1, -20.1], [150.0, -20.0]]],
        [[[151.0, -20.0], [151.1, -20.0], [151.1, -20.1], [151.0, -20.0]]],
    ],
}


def test_km_matches_a_known_distance() -> None:
    # Brisbane GPO to Cairns: about 1,390 km in a straight line.
    assert km((-27.468, 153.028), (-16.920, 145.770)) == pytest.approx(1390, abs=10)
    assert km((-25.0, 153.0), (-25.0, 153.0)) == 0


def test_contains_a_point_inside_but_not_in_the_hole() -> None:
    assert contains(SQUARE, (-25.02, 153.02))
    assert not contains(SQUARE, (-25.05, 153.05))  # in the hole
    assert not contains(SQUARE, (-25.2, 153.02))


def test_contains_works_for_every_part_of_a_multipolygon() -> None:
    assert contains(ISLANDS, (-20.02, 150.05))
    assert contains(ISLANDS, (-20.02, 151.05))
    assert not contains(ISLANDS, (-20.02, 150.5))  # the water between


def test_km_outside_is_zero_inside_and_the_edge_distance_outside() -> None:
    assert km_outside(SQUARE, (-25.02, 153.02)) == 0
    # 0.01° of latitude south of the south edge is about 1.1 km.
    assert km_outside(SQUARE, (-25.11, 153.05)) == pytest.approx(1.11, abs=0.02)
    # In the hole, the nearest edge is the hole's: 0.01° of longitude, about 1 km here.
    assert km_outside(SQUARE, (-25.05, 153.05)) == pytest.approx(1.0, abs=0.05)


def test_bbox_covers_every_part() -> None:
    assert bbox(ISLANDS) == (150.0, -20.1, 151.1, -20.0)
