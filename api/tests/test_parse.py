import dataclasses
from collections.abc import Iterator
from datetime import date

import pytest

from quiet_camps.ingest.clean import State
from quiet_camps.ingest.parse import (
    CampNight,
    each_night,
    parse_family_a,
    parse_family_b,
    parse_family_c,
)

NIGHT = CampNight(
    night=date(2022, 7, 1),
    park="Dalrymple National Park",
    area="Burdekin River camping area",
    adults=1,
    children=0,
    infants=0,
    postcode="4740",
    state=State.QLD,
    booked_on=date(2021, 6, 27),
    reservation_id="1779925",
)


def test_camp_night_is_frozen() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        NIGHT.adults = 2  # type: ignore[misc]  # pyright also rejects this, which is the point


def test_camp_nights_with_the_same_values_are_equal() -> None:
    assert dataclasses.replace(NIGHT) == NIGHT
    assert dataclasses.replace(NIGHT, adults=2) != NIGHT


def test_reservation_id_defaults_to_none() -> None:
    fields = {k: v for k, v in dataclasses.asdict(NIGHT).items() if k != "reservation_id"}

    assert CampNight(**fields).reservation_id is None


# The four family-B layouts, cut down to the same booking. Real header names, real date shapes.
TITLE_CASE = {
    "Camping Reservation Unique ID": "1779925",
    "Type": "Camping",
    "Postcode": "4740",
    "State": "Queensland",
    "Booking Date": "27/06/2021",
    "Start Date": "27/06/2022",
    "Stay Date": "1/07/2022",
    "Park": "Dalrymple National Park",
    "Facility": "Burdekin River camping area",
    "Adults": "1",
    "Children": "0",
    "Infants": "0",
}
SNAKE_CASE = {k.lower().replace(" ", "_"): v for k, v in TITLE_CASE.items()} | {
    "booking_date": "27/06/2021 0:00",
    "start_date": "27/06/2022 0:00",
    "stay_date": "1/07/2022 0:00",
}
RESERVATION_NUMBER = {
    ("Reservation Number" if k == "Camping Reservation Unique ID" else k): v
    for k, v in TITLE_CASE.items()
}
NO_ID = {k: v for k, v in TITLE_CASE.items() if k != "Camping Reservation Unique ID"}


@pytest.mark.parametrize(
    "row",
    [TITLE_CASE, SNAKE_CASE, RESERVATION_NUMBER],
    ids=["title case", "snake_case with 0:00 times", "Reservation Number"],
)
def test_each_family_b_layout_gives_the_same_camp_night(row: dict[str, str]) -> None:
    assert list(parse_family_b([row])) == [NIGHT]


def test_a_layout_without_an_id_gives_none() -> None:
    assert list(parse_family_b([NO_ID])) == [dataclasses.replace(NIGHT, reservation_id=None)]


def test_one_row_in_one_camp_night_out_in_order() -> None:
    second = TITLE_CASE | {"Stay Date": "2/07/2022"}

    nights = list(parse_family_b([TITLE_CASE, second]))

    assert [n.night for n in nights] == [date(2022, 7, 1), date(2022, 7, 2)]


def test_parse_family_b_is_lazy() -> None:
    def rows() -> Iterator[dict[str, str]]:
        yield TITLE_CASE
        raise AssertionError("read past the first row before it was asked for")

    nights = parse_family_b(rows())

    assert next(nights) == NIGHT  # only works if nothing is read ahead


# --- Family C (2025 onwards): one row per booking, expanded into one CampNight per night ---


def test_each_night_counts_from_the_first_night_across_a_month_end() -> None:
    assert list(each_night(date(2025, 6, 30), 3)) == [
        date(2025, 6, 30),
        date(2025, 7, 1),
        date(2025, 7, 2),
    ]


def test_each_night_with_no_nights_gives_nothing() -> None:
    assert list(each_night(date(2025, 6, 30), 0)) == []


BOOKING_ID = {
    "BookingID": "12345678",
    "Type": "Camping",
    "Postcode": "4000",
    "State": "QLD",
    "Booking Date": "02/01/2025",
    "Arrival Date": "30/06/2025",
    "Departure Date": "02/07/2025",
    "Park Name": "K'gari (Fraser Island) Recreation Area",
    "Camping Area": "Dundubara camping area",
    "Adults": "2",
    "Children": "2",
    "Infants": "0",
}
ITINERARY_ID = {
    "Itinerary ID": "12345678",
    "Type": "Accommodation",
    "Postcode": "4000",
    "State": "QLD",
    "Booking Date": "02/01/2025",
    "Start Date": "30/06/2025",
    "Departure Date": "02/07/2025",
    "Park": "K'gari (Fraser Island) Recreation Area",
    "Facility": "Dundubara camping area",
    "Adults": "2",
    "Children": "2",
    "Infants": "0",
}
NO_BOOKING_ID = {k: v for k, v in BOOKING_ID.items() if k != "BookingID"}

FIRST = CampNight(
    night=date(2025, 6, 30),
    park="K'gari (Fraser Island) Recreation Area",
    area="Dundubara camping area",
    adults=2,
    children=2,
    infants=0,
    postcode="4000",
    state=State.QLD,
    booked_on=date(2025, 1, 2),
    reservation_id="12345678",
)
SECOND = dataclasses.replace(FIRST, night=date(2025, 7, 1))


@pytest.mark.parametrize(
    "row", [BOOKING_ID, ITINERARY_ID], ids=["BookingID layout", "Itinerary ID layout"]
)
def test_a_two_night_booking_becomes_two_camp_nights(row: dict[str, str]) -> None:
    # Arrive 30 June, leave 2 July: the nights of 30 June and 1 July.
    assert list(parse_family_c([row])) == [FIRST, SECOND]


def test_family_c_layout_without_an_id_gives_none() -> None:
    assert [n.reservation_id for n in parse_family_c([NO_BOOKING_ID])] == [None, None]


def test_bookings_stay_in_order() -> None:
    one_night = BOOKING_ID | {"BookingID": "2", "Departure Date": "01/07/2025"}

    nights = list(parse_family_c([one_night, BOOKING_ID]))

    assert [(n.reservation_id, n.night) for n in nights] == [
        ("2", date(2025, 6, 30)),
        ("12345678", date(2025, 6, 30)),
        ("12345678", date(2025, 7, 1)),
    ]


def test_parse_family_c_is_lazy() -> None:
    def rows() -> Iterator[dict[str, str]]:
        yield BOOKING_ID
        raise AssertionError("read past the first row before it was asked for")

    nights = parse_family_c(rows())

    assert next(nights) == FIRST
    assert next(nights) == SECOND  # both nights of the first booking, still without reading on


# --- Family A (2011 to June 2016): one row per booking, mixed with vehicle permits ---

OLD_LAYOUT = {  # 2011-2015 export
    "STATE": "QLD",
    "POSTCODE": "4556",
    "BKNG_DATE": "14/03/2013",
    "BKNG_TYPE": "PARK",
    "ITEM_TYPE": "CAMPING",
    "START_DATE": "29/03/2013",
    "DAYS": "2",
    "ADULTS": "4",
    "CHILDREN": "3",
    "LOCATION": "Cooloola Recreation Area",
    "AREA_PERMT": "Teewah Beach camping area",
}
NEW_LAYOUT = {  # April to June 2016 export
    "Postcode": "4556",
    "State": "QLD",
    "Booking Date": "14/03/2013",
    "Item Type": "Camping",
    "Start Date": "29/03/2013",
    "Days": "2",
    "Adults": "4",
    "Children": "3",
    "Location": "Cooloola Recreation Area",
    "Area/Permit Type": "Teewah Beach camping area",
}
EASTER = CampNight(
    night=date(2013, 3, 29),
    park="Cooloola Recreation Area",
    area="Teewah Beach camping area",
    adults=4,
    children=3,
    infants=None,  # not recorded before July 2016
    postcode="4556",
    state=State.QLD,
    booked_on=date(2013, 3, 14),
    reservation_id=None,
)
EASTER_2 = dataclasses.replace(EASTER, night=date(2013, 3, 30))


def without(row: dict[str, str], key: str) -> dict[str, str]:
    return {k: v for k, v in row.items() if k != key}


@pytest.mark.parametrize(
    "row",
    [
        OLD_LAYOUT,
        NEW_LAYOUT,
        without(OLD_LAYOUT, "AREA_PERMT") | {"AREA_PERMIT": "Teewah Beach camping area"},
        without(NEW_LAYOUT, "Area/Permit Type") | {"Area/Permit": "Teewah Beach camping area"},
    ],
    ids=["AREA_PERMT", "Area/Permit Type", "AREA_PERMIT", "Area/Permit"],
)
def test_each_family_a_layout_expands_a_booking_into_nights(row: dict[str, str]) -> None:
    assert list(parse_family_a([row])) == [EASTER, EASTER_2]


@pytest.mark.parametrize("item_type", ["SERVICE", "CAMPING_ADDON", "CREDIT", "Vehicle"])
def test_rows_that_are_not_camping_are_skipped(item_type: str) -> None:
    # Vehicle permits have no party size at all: they must be skipped before int("") fails.
    vehicle = OLD_LAYOUT | {"ITEM_TYPE": item_type, "ADULTS": "", "CHILDREN": "", "DAYS": ""}

    assert list(parse_family_a([vehicle])) == []


def test_camping_rows_among_vehicle_rows_keep_their_order() -> None:
    vehicle = OLD_LAYOUT | {"ITEM_TYPE": "SERVICE", "ADULTS": "", "CHILDREN": ""}
    one_night = OLD_LAYOUT | {"DAYS": "1", "START_DATE": "1/04/2013"}

    nights = list(parse_family_a([vehicle, OLD_LAYOUT, vehicle, one_night]))

    assert [n.night for n in nights] == [date(2013, 3, 29), date(2013, 3, 30), date(2013, 4, 1)]


def test_parse_family_a_is_lazy_even_when_skipping() -> None:
    def rows() -> Iterator[dict[str, str]]:
        yield OLD_LAYOUT | {"ITEM_TYPE": "SERVICE", "ADULTS": ""}
        yield OLD_LAYOUT
        raise AssertionError("read past the first camping row before it was asked for")

    nights = parse_family_a(rows())

    assert next(nights) == EASTER
    assert next(nights) == EASTER_2


# --- Blanks reach the parsers (3c-ii) ---


def test_family_a_blank_children_is_none_not_a_crash() -> None:
    row = OLD_LAYOUT | {"CHILDREN": "", "DAYS": "1"}

    assert [n.children for n in parse_family_a([row])] == [None]


def test_family_b_row_with_no_party_size_still_counts_as_a_night() -> None:
    row = TITLE_CASE | {"Adults": "", "Children": "", "Infants": ""}

    assert list(parse_family_b([row])) == [
        dataclasses.replace(NIGHT, adults=None, children=None, infants=None)
    ]


def test_parsers_clean_the_postcode() -> None:
    row = TITLE_CASE | {"Postcode": "810"}

    assert [n.postcode for n in parse_family_b([row])] == ["0810"]


def test_parsers_clean_the_state() -> None:
    row = TITLE_CASE | {"State": "Qld"}

    assert [n.state for n in parse_family_b([row])] == [State.QLD]
