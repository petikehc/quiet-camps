"""Plain words to dates and a place: "next weekend around Sunshine Coast". A model reads the
words (bedrock_reader.py); this checks what it read and finds the place (ADR 0005)."""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from quiet_camps.api.place_service import Place, PlaceSource, find_place
from quiet_camps.api.search import MAX_NIGHTS, NEAR_KM

STAY_NIGHTS = 2  # arriving with no leaving day: a weekend
# How far to look when they don't say: a weekend's drive from home, or around a place.
DEFAULT_KM = {"from": 150, "near": 50}


class Reading(BaseModel):
    """What someone asked for, as the model read it. Whatever they didn't say is None."""

    arrive: date | None = Field(description="The first night, YYYY-MM-DD")
    depart: date | None = Field(description="The morning they leave, YYYY-MM-DD")
    place: str | None = Field(description="One Queensland town, suburb, council area or park")
    place_role: Literal["from", "near"] | None = Field(
        description="from: where they set out from; near: where they want to camp"
    )
    within_km: int | None = Field(description="Only if they said a distance or a drive time")


@dataclass(frozen=True, kw_only=True)
class Holiday:
    """A public holiday's nights, for reading "Easter" or "the long weekend"."""

    name: str
    arrive: date  # its first night
    depart: date  # the morning after its last night


class Reader(Protocol):
    async def read(self, text: str, today: date, holidays: list[Holiday]) -> Reading: ...


class ReaderUnavailable(Exception):
    """The model couldn't be asked, or didn't answer: the page falls back to its own fields."""


@dataclass(frozen=True, kw_only=True)
class Answer:
    arrive: date | None
    depart: date | None
    place: Place | None
    place_asked: str | None  # what they called the place, when nothing matched it
    place_role: Literal["from", "near"] | None
    within_km: int | None  # only with a place


def stay(arrive: date | None, depart: date | None, today: date) -> tuple[date, date] | None:
    """The nights asked for, made sense of: none in the past, a weekend if no end, 60 at most."""
    if arrive is None or arrive < today:
        return None
    if depart is None or depart <= arrive:
        depart = arrive + timedelta(days=STAY_NIGHTS)
    return arrive, min(depart, arrive + timedelta(days=MAX_NIGHTS))


async def ask(
    reader: Reader, places: PlaceSource, text: str, today: date, holidays: list[Holiday]
) -> Answer:
    reading = await reader.read(text, today, holidays)
    nights = stay(reading.arrive, reading.depart, today)
    place = None if reading.place is None else await find_place(places, reading.place)
    role = reading.place_role or ("near" if reading.place else None)
    km = None
    if place is not None and role is not None:
        km = max(NEAR_KM[0], min(NEAR_KM[1], reading.within_km or DEFAULT_KM[role]))
    return Answer(
        arrive=None if nights is None else nights[0],
        depart=None if nights is None else nights[1],
        place=place,
        place_asked=reading.place if place is None else None,
        place_role=role if reading.place else None,
        within_km=km,
    )
