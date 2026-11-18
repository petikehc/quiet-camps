import dataclasses
from collections.abc import Iterator
from datetime import date

import pytest

from quiet_camps.ingest.parse import CampNight, parse_family_b

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
