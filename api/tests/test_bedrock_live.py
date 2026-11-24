"""One real ask of Claude on Bedrock: a fraction of a cent. Runs only with RUN_LIVE_AWS=1,
with the reader the settings pick (ASK_ENDPOINT, ASK_MODEL, AWS_PROFILE, AWS_REGION)."""

import asyncio
import os
from datetime import date

import pytest

from quiet_camps.api.ask_service import Holiday
from quiet_camps.api.bedrock_reader import make_reader
from quiet_camps.api.settings import Settings

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_AWS") != "1", reason="calls AWS: set RUN_LIVE_AWS=1"
)


def test_easter_near_noosa() -> None:
    reader = make_reader(Settings())
    easter = Holiday(name="easter", arrive=date(2027, 3, 25), depart=date(2027, 3, 29))

    reading = asyncio.run(reader.read("easter near noosa", date(2026, 11, 23), [easter]))

    assert (reading.arrive, reading.depart) == (easter.arrive, easter.depart)
    assert (reading.place, reading.place_role) == ("Noosa", "near")
