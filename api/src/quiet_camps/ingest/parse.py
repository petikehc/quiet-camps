from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import date, timedelta

from quiet_camps.ingest.clean import normalise, parse_date

FAMILY_A_BOOKING_DATE_COLUMNS = ("booking date", "bkng date")
FAMILY_A_AREA_COLUMNS = ("area/permit type", "area/permit", "area permit", "area permt")

FAMILY_B_ID_COLUMNS = ("camping reservation unique id", "reservation number")

FAMILY_C_ID_COLUMNS = ("bookingid", "itinerary id")
FAMILY_C_ARRIVAL_COLUMNS = ("arrival date", "start date")
FAMILY_C_PARK_COLUMNS = ("park name", "park")
FAMILY_C_AREA_COLUMNS = ("camping area", "facility")


@dataclass(frozen=True, slots=True)
class CampNight:
    night: date
    booked_on: date
    park: str
    area: str
    adults: int
    children: int
    infants: int | None
    postcode: str
    state: str
    reservation_id: str | None = None


def first_present(row: dict[str, str], names: tuple[str, ...]) -> str | None:
    for col in names:
        if col in row:
            return row[col]
    return None


def require(row: dict[str, str], names: tuple[str, ...]) -> str:
    fp = first_present(row, names)

    if fp is None:
        raise KeyError(f"none of {names} in row")

    return fp


def each_night(first: date, count: int) -> Iterator[date]:
    for n in range(count):
        yield first + timedelta(days=n)


def normalise_keys(row: dict[str, str]) -> dict[str, str]:
    return {normalise(k): v for k, v in row.items()}


def parse_family_a(rows: Iterable[dict[str, str]]) -> Iterator[CampNight]:
    for row in rows:
        normalised = normalise_keys(row)

        if normalised["item type"].casefold() != "camping":
            continue

        arrival = parse_date(normalised["start date"])
        nights = int(normalised["days"])

        for night in each_night(arrival, nights):
            yield CampNight(
                night=night,
                booked_on=parse_date(require(normalised, FAMILY_A_BOOKING_DATE_COLUMNS)),
                park=normalised["location"],
                area=require(normalised, FAMILY_A_AREA_COLUMNS),
                adults=int(normalised["adults"]),
                children=int(normalised["children"]),
                infants=None,
                postcode=normalised["postcode"],
                state=normalised["state"],
                reservation_id=None,
            )


def parse_family_b(rows: Iterable[dict[str, str]]) -> Iterator[CampNight]:
    for row in rows:
        normalised = normalise_keys(row)

        cn = CampNight(
            night=parse_date(normalised["stay date"]),
            booked_on=parse_date(normalised["booking date"]),
            park=normalised["park"],
            area=normalised["facility"],
            adults=int(normalised["adults"]),
            children=int(normalised["children"]),
            infants=int(normalised["infants"]),
            postcode=normalised["postcode"],
            state=normalised["state"],
            reservation_id=first_present(normalised, FAMILY_B_ID_COLUMNS),
        )

        yield cn


def parse_family_c(rows: Iterable[dict[str, str]]) -> Iterator[CampNight]:
    for row in rows:
        normalised = normalise_keys(row)
        arrival = parse_date(require(normalised, FAMILY_C_ARRIVAL_COLUMNS))
        departure = parse_date(normalised["departure date"])

        for night in each_night(arrival, (departure - arrival).days):
            yield CampNight(
                night=night,
                booked_on=parse_date(normalised["booking date"]),
                park=require(normalised, FAMILY_C_PARK_COLUMNS),
                area=require(normalised, FAMILY_C_AREA_COLUMNS),
                adults=int(normalised["adults"]),
                children=int(normalised["children"]),
                infants=int(normalised["infants"]),
                postcode=normalised["postcode"],
                state=normalised["state"],
                reservation_id=first_present(normalised, FAMILY_C_ID_COLUMNS),
            )
