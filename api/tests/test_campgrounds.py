import pytest

from quiet_camps.ingest.campgrounds import (
    MERGES_CSV,
    area_key,
    campground_key,
    load_merges,
    park_key,
    suggest_merges,
)

# Every name Dundubara on K'gari has had in the permit files, 2011-2026.
DUNDUBARA = [
    ("Fraser Island (Great Sandy National Park)", "Dundubara camping area"),
    ("Fraser Island (Great Sandy National Park)", "Dundubara tent camping"),
    ("Fraser Island (Great Sandy National Park)", "Dundubara - trailer sites"),
    ("Fraser Island (Great Sandy National Park)", "Dundubara group area (not for use by SSQ)"),
    ("Fraser Island (Great Sandy National Park)", "Dundubara Commercial Operator Site"),
    ("Fraser Island Recreation Area", "Dundubara (Tent Site) camping area"),
    ("Fraser Island Recreation Area", "Dundubara CTO Site"),
    ("K'gari (Fraser Island) Recreation Area", "Dundubara (trailer site) camping area"),
    ("K'gari (Fraser Island) Recreation Area", "Dundubara group camping area"),
    ("K'gari (Fraser Island) Recreation Area", "Dundubara camping area"),
]


def test_every_name_dundubara_has_had_is_one_campground() -> None:
    assert {campground_key(park, area, {}) for park, area in DUNDUBARA} == {("kgari", "dundubara")}


@pytest.mark.parametrize(
    ("park", "expected"),
    [
        ("K'gari (Fraser Island) Recreation Area", "kgari"),  # brackets: the old name
        ("Fraser Island Great Walk", "kgari"),  # an alias, after "great walk" goes
        ("Carnarvon Gorge (Carnarvon National Park)", "carnarvon"),  # brackets: the parent park
        ("Byfield State Forest and National Park", "byfield"),
        ("Hinchinbrook Island NP, Thorsborne Trail", "hinchinbrook island"),  # after a comma
        ("Thorsborne Trail,Hinchinbrook Island National Park", "hinchinbrook island"),
        ("Daintree National Park (CYPAL)", "daintree"),
        ("Apudthama National Park (CYPAL)", "jardine river heathlands"),  # renamed in 2025
        ("Jardine River National Park", "jardine river heathlands"),
        ("D Aguilar National Park", "daguilar"),
        ("D'Aguilar National Park", "daguilar"),
    ],
)
def test_park_renames_and_regroupings_meet(park: str, expected: str) -> None:
    assert park_key(park) == expected


@pytest.mark.parametrize(
    ("area", "expected"),
    [
        ("Garry's Anchorage campground", "garrys anchorage"),
        ("Garry\u2019s Anchorage camping area", "garrys anchorage"),
        ("Garry?s Anchorage camping area", "garrys anchorage"),  # cp1252 quote, decoded badly
        ("Garry\x92s Anchorage camping area", "garrys anchorage"),
        ("Terrawambella (trailer/tent sites) camping areaOLD", "terrawambella"),
        ("Castle Rock camping area trailer or van sites", "castle rock"),
        ("Castle Rock camping area (PWD sites)", "castle rock"),
        ("M.V. Sarawak camping area", "mv sarawak"),
        ("Mt Huntley remote bush camp", "mount huntley bush"),
        ("Lake Wabby (Great Walk campsites)", "lake wabby great walk"),
        ("Lake Wabby great walk camp sites", "lake wabby great walk"),
    ],
)
def test_spelling_and_booking_labels_are_not_part_of_the_name(area: str, expected: str) -> None:
    assert area_key(area) == expected


@pytest.mark.parametrize(
    ("one", "other"),
    [
        ("Dundubara camping area", "Central Station camping area"),
        ("Cornwells camping area", "Cornwells camping area (fenced)"),  # a dingo fence
        ("Noosa River camp site 1", "Noosa River camp site 13"),
        ("Waddy Point top camping area", "Waddy Point beachfront camping area"),
    ],
)
def test_different_places_stay_apart(one: str, other: str) -> None:
    assert area_key(one) != area_key(other)


def test_the_same_area_name_in_unrelated_parks_stays_apart() -> None:
    park_a, park_b = "Moreton Island National Park", "Bribie Island Recreation Area"
    assert campground_key(park_a, "Beach camping", {}) != campground_key(
        park_b, "Beach camping", {}
    )


def test_a_reviewed_merge_joins_a_typo_to_the_right_name() -> None:
    merges = {("kgari", "central station geat walk"): ("kgari", "central station great walk")}
    typo = campground_key(
        "Fraser Island Great Walk", "Central Station (Geat Walk campsites)", merges
    )
    assert typo == campground_key(
        "K'gari (Fraser Island) Great Walk", "Central Station great walk camp sites", merges
    )


def test_the_merges_csv_is_written_in_keys_and_never_chains() -> None:
    merges = load_merges(MERGES_CSV)
    assert merges
    for (park, area), (same_park, same_as) in merges.items():
        assert park == same_park
        assert area_key(area) == area, "write the area as its key"
        assert area_key(same_as) == same_as
        assert (park, same_as) not in merges, f"{same_as!r} is merged again: point at the end"


def test_suggestions_find_typos() -> None:
    keys = [("cooloola", "fig tree point"), ("cooloola", "figtree point")]
    [suggestion] = suggest_merges(keys)
    assert (suggestion.park, suggestion.area, suggestion.same_as) == (
        "cooloola",
        "fig tree point",
        "figtree point",
    )


@pytest.mark.parametrize(
    ("one", "other"),
    [
        ("noosa river 1", "noosa river 13"),  # scores 96, but a different site
        ("north kobble bush", "south kobble bush"),
        ("harrys hut a", "harrys hut b"),
        ("noosa river 1", "upper noosa river 1"),
    ],
)
def test_suggestions_skip_names_with_different_numbers_or_directions(one: str, other: str) -> None:
    assert suggest_merges([("p", one), ("p", other)], threshold=0) == []


def test_suggestions_never_cross_parks() -> None:
    assert suggest_merges([("cooloola", "fig tree point"), ("byfield", "figtree point")]) == []
