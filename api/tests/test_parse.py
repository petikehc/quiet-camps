import dataclasses
from collections.abc import Iterator
from datetime import date

import pytest

from quiet_camps.ingest.parse import CampNight, each_night, parse_family_b, parse_family_c

NIGHT = CampNight(
    night=date(2022, 7, 1),
    park="Dalrymple National Park",
    area="Burdekin River camping area",
    adults=1,
    children=0,
    infants=0,
    postcode="4740",
    state="Queensland",
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
    state="QLD",
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
