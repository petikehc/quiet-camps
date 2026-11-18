from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import date

from quiet_camps.ingest.clean import parse_date
from quiet_camps.ingest.profile_report import normalise

ID_COLUMNS = ("camping reservation unique id", "reservation number")


@dataclass(frozen=True, slots=True)
class CampNight:
    night: date
    booked_on: date
    park: str
    area: str
    adults: int
    children: int
    infants: int
    postcode: str
    state: str
    reservation_id: str | None = None


def first_present(row: dict[str, str], names: tuple[str, ...]) -> str | None:
    for col in names:
        if col in row:
            return row[col]
    return None


def parse_family_b(rows: Iterable[dict[str, str]]) -> Iterator[CampNight]:
    for row in rows:
        normalised = {normalise(k): v for k, v in row.items()}

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
            reservation_id=first_present(normalised, ID_COLUMNS),
        )

        yield cn
