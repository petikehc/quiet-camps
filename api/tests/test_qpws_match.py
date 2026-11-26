import pytest

from quiet_camps.ingest.qpws import CampingPage, ParkPage
from quiet_camps.ingest.qpws_match import QpwsLink, qpws_link

# Real entries from QPWS's camping areas and parks A to Z listings (October 2026).
PARKS = "https://parks.qld.gov.au/parks/"


def camping(path: str, name: str, park_name: str) -> CampingPage:
    return CampingPage(f"{PARKS}{path}", name, park_name)


ALLIGATOR_CREEK = camping(
    "bowling-green-bay/camping/alligator-creek",
    "Alligator Creek camping area, Mount Elliot",
    "Bowling Green Bay National Park",
)
ALLIGATOR_FALLS = camping(
    "bowling-green-bay/camping/alligator-falls",
    "Alligator Falls camping area, Mount Elliot",
    "Bowling Green Bay National Park",
)
TOP_MOFFATT = camping(
    "carnarvon-mount-moffatt/camping/top-moffatt-mount-moffatt",
    "Top Moffatt (Mount Moffatt section) camping area",
    "Mount Moffatt, Carnarvon National Park",
)
THORSBORNE = camping(
    "hinchinbrook-thorsborne/camping/thorsborne-trail",
    "Thorsborne Trail",
    "Thorsborne Trail, Hinchinbrook Island National Park",
)
CENTRAL_STATION_TENT = camping(
    "kgari-fraser/camping/central-station-tent",
    "Central Station (tent site) camping area",
    "K'gari, Great Sandy National Park",
)
CENTRAL_STATION_TRAILER = camping(
    "kgari-fraser/camping/central-station-trailer",
    "Central Station (trailer site) camping area",
    "K'gari, Great Sandy National Park",
)
CENTRAL_STATION_WALKERS = camping(
    "great-walks-kgari-fraser/camping/central-station",
    "Central Station great walk camp sites",
    "K'gari Great Walk",
)
MOUNT_MAY_SADDLE = camping(
    "mount-barney/camping/mount-may-saddle-remote",
    "Mount May Saddle remote bush camp",
    "Mount Barney National Park",
)
JEFFRIES_BEACH = camping(
    "great-sandy-woody/camping/jeffries-beach",
    "Jeffries Beach",
    "Woody Island (Tooliewah) and Little Woody Island (Walangoora), Great Sandy National Park",
)
CAMPING = [
    ALLIGATOR_CREEK,
    ALLIGATOR_FALLS,
    TOP_MOFFATT,
    THORSBORNE,
    CENTRAL_STATION_TENT,
    CENTRAL_STATION_TRAILER,
    CENTRAL_STATION_WALKERS,
    MOUNT_MAY_SADDLE,
    JEFFRIES_BEACH,
]

MAIN_RANGE = ParkPage(f"{PARKS}main-range", "Main Range National Park")
MAIN_RANGE_CP = ParkPage(f"{PARKS}main-range-cp", "Main Range Conservation Park")
MOUNT_BARNEY = ParkPage(f"{PARKS}mount-barney", "Mount Barney National Park")


def link(park: str, name: str, parks: list[ParkPage] | None = None) -> QpwsLink | None:
    return qpws_link(park, name, CAMPING, parks or [])


def test_the_closest_name_in_the_park_wins() -> None:
    # QPWS adds the section after a comma: "Alligator Creek camping area, Mount Elliot".
    assert link("Bowling Green Bay National Park", "Alligator Creek camping area") == QpwsLink(
        ALLIGATOR_CREEK.url, "camping"
    )


def test_a_park_section_is_the_same_park() -> None:
    # "Mount Moffatt, Carnarvon National Park" and "Carnarvon National Park" share a park key.
    assert link(
        "Carnarvon National Park", "Top Moffatt (Mount Moffatt section) camping area"
    ) == QpwsLink(TOP_MOFFATT.url, "camping")


@pytest.mark.parametrize(
    "name",
    [
        "Thorsborne Trail",
        "Thorsborne Trail - 2 nights/3 days",
        "Thorsborne Trail - 3 nights/4 days",
    ],
)
def test_every_trail_permit_links_to_the_trail(name: str) -> None:
    assert link("Hinchinbrook Island NP, Thorsborne Trail", name) == QpwsLink(
        THORSBORNE.url, "camping"
    )


def test_tent_and_trailer_pages_are_one_place() -> None:
    # The Great Walk is the same park ("kgari") and the same match key ("central station"), so
    # three pages tie. The full area key breaks it ("central station", not "... great walk"),
    # and what's still tied is one place listed twice: take the first page, by URL.
    assert link("K'gari (Fraser Island) Recreation Area", "Central Station camping area") == (
        QpwsLink(CENTRAL_STATION_TENT.url, "camping")
    )


def test_the_great_walk_camp_links_to_the_walkers_page() -> None:
    assert link("K'gari (Fraser Island) Great Walk", "Central Station great walk camp sites") == (
        QpwsLink(CENTRAL_STATION_WALKERS.url, "camping")
    )


def test_an_exact_name_in_another_park_counts() -> None:
    # Our park is "Woody Island"; QPWS files it under Great Sandy National Park.
    assert link("Woody Island", "Jeffries Beach") == QpwsLink(JEFFRIES_BEACH.url, "camping")


def test_a_similar_name_in_another_park_does_not_count() -> None:
    # "Mount Huntley Saddle" is close to Mount Barney's "Mount May Saddle", but it's in Main
    # Range: link to the park instead.
    assert link(
        "Main Range National Park",
        "Mount Huntley Saddle remote bush camp",
        [MAIN_RANGE, MOUNT_BARNEY],
    ) == QpwsLink(MAIN_RANGE.url, "park")


def test_no_link_when_two_park_pages_share_our_park() -> None:
    # "Main Range Conservation Park" and "Main Range National Park" are both "main range".
    assert (
        link(
            "Main Range National Park",
            "Steamer Creek remote bush camp",
            [MAIN_RANGE, MAIN_RANGE_CP],
        )
        is None
    )
