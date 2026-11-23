"""One real ask of Claude on Bedrock: a fraction of a cent. Runs only with RUN_LIVE_AWS=1."""

import asyncio
import os
from datetime import date

import pytest
from anthropic.lib.bedrock import AsyncAnthropicBedrockMantle

from quiet_camps.api.ask_service import Holiday
from quiet_camps.api.bedrock_reader import BedrockReader
from quiet_camps.api.settings import Settings

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_AWS") != "1", reason="calls AWS: set RUN_LIVE_AWS=1"
)


def test_easter_near_noosa() -> None:
    settings = Settings()
    client = AsyncAnthropicBedrockMantle(
        aws_region=settings.aws_region, aws_profile=settings.aws_profile
    )
    reader = BedrockReader(client, settings.ask_model, settings.ask_effort)
    easter = Holiday(name="easter", arrive=date(2027, 3, 25), depart=date(2027, 3, 29))

    reading = asyncio.run(reader.read("easter near noosa", date(2026, 11, 23), [easter]))

    assert (reading.arrive, reading.depart) == (easter.arrive, easter.depart)
    assert (reading.place, reading.place_role) == ("Noosa", "near")
