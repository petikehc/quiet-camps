"""The Bedrock reader's request and its failures, with a fake client: no AWS."""

import asyncio
from dataclasses import dataclass
from datetime import date
from typing import Any, cast

import anthropic
import httpx2  # the SDK's own httpx
import pytest
from anthropic.lib.bedrock import AsyncAnthropicBedrockMantle

from quiet_camps.api.ask_service import Holiday, ReaderUnavailable, Reading
from quiet_camps.api.bedrock_reader import BedrockReader

TODAY = date(2026, 11, 23)
EASTER = Holiday(name="easter", arrive=date(2027, 3, 25), depart=date(2027, 3, 29))
READING = Reading(arrive=None, depart=None, place="Noosa", place_role="near", within_km=None)


@dataclass
class Parsed:
    stop_reason: str
    parsed_output: Reading | None


class FakeMessages:
    def __init__(self, result: Parsed | Exception) -> None:
        self.result = result
        self.asked: dict[str, Any] = {}

    async def parse(self, **kwargs: Any) -> Parsed:
        self.asked = kwargs
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakeClient:
    def __init__(self, result: Parsed | Exception) -> None:
        self.messages = FakeMessages(result)


def read(result: Parsed | Exception) -> tuple[Reading, FakeClient]:
    client = FakeClient(result)
    reader = BedrockReader(cast(AsyncAnthropicBedrockMantle, client), "anthropic.claude-haiku-5-5")
    return asyncio.run(reader.read("Easter near Noosa", TODAY, [EASTER])), client


def test_asks_haiku_for_a_reading_with_the_calendar() -> None:
    reading, client = read(Parsed("end_turn", READING))

    asked = client.messages.asked
    assert reading == READING
    assert asked["model"] == "anthropic.claude-haiku-5-5"
    assert asked["output_format"] is Reading
    assert asked["output_config"] == {"effort": "low"}
    content = asked["messages"][0]["content"]
    assert "Today is Monday 23 November 2026." in content
    assert "- easter: arrive Thu 25 Mar 2027, depart Mon 29 Mar 2027" in content
    assert content.endswith("<request>Easter near Noosa</request>")


def test_a_refusal_is_unavailable() -> None:
    with pytest.raises(ReaderUnavailable):
        read(Parsed("refusal", None))


def test_an_api_error_is_unavailable() -> None:
    error = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://bedrock"))
    with pytest.raises(ReaderUnavailable):
        read(error)
