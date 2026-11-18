from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import date

from quiet_camps.ingest.clean import parse_date
from quiet_camps.ingest.profile_report import normalise


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


def parse_family_b(rows: Iterable[dict[str, str]]) -> Iterator[CampNight]:
    for row in rows:
        normalised = {normalise(k): v for k, v in row.items()}

        if "camping reservation unique id" in normalised:
            reservation_id = normalised["camping reservation unique id"]
        elif "reservation number" in normalised:
            reservation_id = normalised["reservation number"]
        else:
            reservation_id = None

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
            reservation_id=reservation_id,
        )

        yield cn
