"""Plain words to dates and a place: "next weekend around Sunshine Coast". A model reads the
words (bedrock_reader.py); this checks what it read and finds the place (ADR 0005)."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal, Protocol

import holidays as public_holidays
from pydantic import BaseModel, Field

from quiet_camps.api.place_service import Place, PlaceSource, find_place
from quiet_camps.api.search import MAX_NIGHTS, NEAR_KM
from quiet_camps.ingest.school_holidays import SchoolHoliday

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
    """A holiday's nights, for reading "Easter", "the long weekend" or "school holidays"."""

    name: str
    arrive: date  # its first night
    depart: date  # the morning after its last night


SATURDAY = 5  # date.weekday()
WEEK = timedelta(days=7)
AHEAD = timedelta(days=365)  # as far as the public holidays the model is given


def first_week(holiday: SchoolHoliday) -> Holiday:
    """ "School holidays" read as a trip: a week from the first Saturday off (the holidays may
    start on Good Friday), cut short if they end sooner."""
    first_day = holiday.first_night + timedelta(days=1)
    arrive = first_day + timedelta(days=(SATURDAY - first_day.weekday()) % 7)
    return Holiday(
        name=f"{holiday.name} school holidays, first week",
        arrive=arrive,
        depart=min(arrive + WEEK, holiday.last_night + timedelta(days=1)),
    )


def queensland_holidays(today: date) -> Mapping[date, str]:
    """Queensland's public holidays this year and next, by date."""
    return public_holidays.country_holidays("AU", subdiv="QLD", years=[today.year, today.year + 1])


def long_weekends(today: date, public: Mapping[date, str] | None = None) -> list[Holiday]:
    """Runs of three or more days off (a public holiday joined to a weekend) in the next year,
    as stays: from the night before the first day off to the morning of the last. Worked out
    here, so "the next long weekend" is never the model's arithmetic."""
    public = queensland_holidays(today) if public is None else public

    def day_off(day: date) -> bool:
        return day.weekday() >= SATURDAY or day in public

    weekends: list[Holiday] = []
    for day in sorted(d for d in public if today < d <= today + AHEAD):
        if weekends and day <= weekends[-1].depart:
            continue  # inside the run already found (Christmas and Boxing Day)
        start, end = day, day
        while day_off(start - timedelta(days=1)):
            start -= timedelta(days=1)
        while day_off(end + timedelta(days=1)):
            end += timedelta(days=1)
        if (end - start).days + 1 >= 3:
            name = public[day].split("; ")[0]
            weekends.append(
                Holiday(name=f"{name} long weekend", arrive=start - timedelta(days=1), depart=end)
            )
    return weekends


def coming_school_holidays(today: date, holidays: list[SchoolHoliday]) -> list[Holiday]:
    """The first weeks still to come in the next year, so the model copies dates and never
    works them out."""
    weeks = [first_week(h) for h in holidays]
    return [w for w in weeks if today <= w.arrive <= today + AHEAD]


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
