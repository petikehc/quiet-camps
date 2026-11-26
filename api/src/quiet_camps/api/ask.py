"""POST /ask: plain words to dates and a place, read by Claude on Amazon Bedrock (ADR 0005).

Guarded because every call costs money: off unless switched on, 200 characters at most,
the same words answered from a cache for the rest of the day, and limits counted in Postgres
(ask_limits.py): 20 an hour per viewer and 300 a day for the whole site. The words themselves
are never stored or logged.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from quiet_camps.api.ask_limits import SITE, count_ask, day_start, hour_start, viewer_bucket
from quiet_camps.api.ask_service import (
    Answer,
    Holiday,
    Reader,
    ReaderUnavailable,
    ask,
    coming_school_holidays,
    long_weekends,
)
from quiet_camps.api.campground_repository import HOLIDAY_NIGHTS
from quiet_camps.api.campground_service import HolidayNight, holiday_spans
from quiet_camps.api.db import get_session
from quiet_camps.api.origin import client_ip
from quiet_camps.api.place_service import PlaceSource
from quiet_camps.api.places import PlaceOut, get_place_source
from quiet_camps.api.problems import INVALID, Problem
from quiet_camps.api.settings import Settings
from quiet_camps.ingest.school_holidays import school_holidays

log = logging.getLogger(__name__)

CACHED = 500  # answers kept; the cache empties when the day changes
QUEENSLAND = ZoneInfo("Australia/Brisbane")  # no daylight saving: "today" is Queensland's

ask_router = APIRouter(
    responses={
        **INVALID,
        429: {"model": Problem, "description": "Too many asks from here; try again later"},
        503: {"model": Problem, "description": "Asking is switched off or unavailable"},
    }
)


class AskIn(BaseModel):
    text: str = Field(min_length=3, max_length=200)  # "next weekend around Sunshine Coast"


class AskOut(BaseModel):
    """What was understood. Anything not understood is None, for the page to ask itself."""

    model_config = ConfigDict(from_attributes=True)

    arrive: date | None
    depart: date | None
    place: PlaceOut | None
    place_asked: str | None  # what they called the place, when nothing matched it
    place_role: Literal["from", "near"] | None
    within_km: int | None


class AskState:
    """Per app: the day's answers, and the reader once it's first needed."""

    def __init__(self) -> None:
        self.day: date | None = None
        self.answers: dict[str, AskOut] = {}
        self.reader: Reader | None = None


def ask_state(request: Request) -> AskState:
    state: AskState = request.app.state.ask
    return state


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_today() -> date:
    return datetime.now(QUEENSLAND).date()


def reader_for(state: AskState, settings: Settings) -> Reader:
    """Made on the first ask, so a switched-off API never builds an AWS client. Tests put a
    fake reader in AskState instead."""
    if state.reader is None:
        # Imported here too: boto3 and the Anthropic SDK are half of a cold start's imports.
        from quiet_camps.api.bedrock_reader import make_reader

        state.reader = make_reader(settings)
    return state.reader


async def coming_holidays(session: AsyncSession, today: date) -> list[Holiday]:
    """The next year's public holidays from the calendar, so the model needn't work out Easter,
    its long weekends, and the school holidays' first weeks, in date order."""
    last = today + timedelta(days=365)
    rows = await session.execute(HOLIDAY_NIGHTS, {"first": today, "last": last})
    spans = holiday_spans([HolidayNight(**row) for row in rows.mappings()], today)
    public = [
        Holiday(
            name=s.name,
            arrive=today + timedelta(days=s.night),
            depart=today + timedelta(days=s.night + s.nights),
        )
        for s in spans
    ]
    school = coming_school_holidays(today, school_holidays())
    return sorted([*public, *long_weekends(today), *school], key=lambda h: h.arrive)


def normalised(text: str) -> str:
    return " ".join(text.lower().split())


@ask_router.post("/ask")
async def ask_in_plain_words(
    body: AskIn,
    request: Request,
    state: Annotated[AskState, Depends(ask_state)],
    settings: Annotated[Settings, Depends(get_settings)],
    today: Annotated[date, Depends(get_today)],
    session: Annotated[AsyncSession, Depends(get_session)],
    places: Annotated[PlaceSource, Depends(get_place_source)],
) -> AskOut:
    if not settings.ask_enabled:
        raise HTTPException(503, "Asking in plain words is switched off: choose dates and a place.")
    if state.day != today:
        state.day, state.answers = today, {}
    key = normalised(body.text)
    if key in state.answers:  # answered today already: free, and not counted
        return state.answers[key]
    viewer = viewer_bucket(client_ip(request, settings.client_ip_header))
    if (
        await count_ask(session, viewer, hour_start(datetime.now(QUEENSLAND)))
        > settings.ask_per_hour
    ):
        raise HTTPException(
            429, "That's a lot of asking: try again in an hour.", {"Retry-After": "3600"}
        )
    # The site's cap: however many viewers, at most this many calls to the model a day.
    if await count_ask(session, SITE, day_start(today)) > settings.ask_per_day:
        raise HTTPException(
            503, "Plain words are resting until tomorrow: choose dates and a place."
        )

    reader = reader_for(state, settings)
    try:
        answer: Answer = await ask(
            reader, places, body.text, today, await coming_holidays(session, today)
        )
    except ReaderUnavailable as e:
        log.warning("ask unavailable: %s", e)
        raise HTTPException(503, "Couldn't read that just now: choose dates and a place.") from e
    # Counts only: what was understood, never the words.
    log.info("ask: dates=%s place=%s", answer.arrive is not None, answer.place is not None)
    out = AskOut.model_validate(answer)
    if len(state.answers) < CACHED:
        state.answers[key] = out
    return out
