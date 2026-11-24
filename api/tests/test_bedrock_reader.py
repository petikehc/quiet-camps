"""The Bedrock readers' requests and their failures, with fake clients: no AWS."""

import asyncio
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal, cast

import anthropic
import httpx2  # the SDK's own httpx
import pytest
from anthropic.lib.bedrock import AsyncAnthropicBedrockMantle
from botocore.exceptions import ClientError
from mypy_boto3_bedrock_runtime import BedrockRuntimeClient

from quiet_camps.api.ask_service import Holiday, ReaderUnavailable, Reading
from quiet_camps.api.bedrock_reader import ConverseReader, MantleReader

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


def read(
    result: Parsed | Exception, effort: Literal["low"] | None = None
) -> tuple[Reading, FakeClient]:
    client = FakeClient(result)
    model = "anthropic.claude-haiku-4-5"
    reader = MantleReader(cast(AsyncAnthropicBedrockMantle, client), model, effort)
    return asyncio.run(reader.read("Easter near Noosa", TODAY, [EASTER])), client


def test_asks_haiku_for_a_reading_with_the_calendar() -> None:
    reading, client = read(Parsed("end_turn", READING))

    asked = client.messages.asked
    assert reading == READING
    assert asked["model"] == "anthropic.claude-haiku-4-5"
    assert asked["output_format"] is Reading
    assert asked["output_config"] == {}  # Haiku 4.5 takes no effort
    content = asked["messages"][0]["content"]
    assert "Today is Monday 23 November 2026." in content
    assert "Coming holidays:" in content
    assert "- easter: arrive Thu 25 Mar 2027, depart Mon 29 Mar 2027" in content
    assert content.endswith("<request>Easter near Noosa</request>")


def test_an_effort_is_sent_when_set() -> None:
    _, client = read(Parsed("end_turn", READING), effort="low")

    assert client.messages.asked["output_config"] == {"effort": "low"}


def test_a_refusal_is_unavailable() -> None:
    with pytest.raises(ReaderUnavailable):
        read(Parsed("refusal", None))


def test_an_api_error_is_unavailable() -> None:
    error = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://bedrock"))
    with pytest.raises(ReaderUnavailable):
        read(error)


class FakeRuntime:
    """bedrock-runtime's converse, by shape: records the request, answers or raises."""

    def __init__(self, result: dict[str, Any] | Exception) -> None:
        self.result = result
        self.asked: dict[str, Any] = {}

    def converse(self, **kwargs: Any) -> dict[str, Any]:
        self.asked = kwargs
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def answered(*content: dict[str, Any], stop: str = "tool_use") -> dict[str, Any]:
    return {
        "output": {"message": {"role": "assistant", "content": list(content)}},
        "stopReason": stop,
    }


def converse(result: dict[str, Any] | Exception) -> tuple[Reading, FakeRuntime]:
    runtime = FakeRuntime(result)
    model = "au.anthropic.claude-haiku-4-5-20251001-v1:0"
    reader = ConverseReader(cast(BedrockRuntimeClient, runtime), model)
    return asyncio.run(reader.read("Easter near Noosa", TODAY, [EASTER])), runtime


def test_converse_forces_the_reading_tool() -> None:
    tool_use = {"toolUse": {"toolUseId": "t1", "name": "reading", "input": READING.model_dump()}}
    reading, runtime = converse(answered(tool_use))

    asked = runtime.asked
    assert reading == READING
    assert asked["modelId"] == "au.anthropic.claude-haiku-4-5-20251001-v1:0"
    assert asked["toolConfig"]["toolChoice"] == {"tool": {"name": "reading"}}
    schema = asked["toolConfig"]["tools"][0]["toolSpec"]["inputSchema"]["json"]
    assert set(schema["properties"]) == {"arrive", "depart", "place", "place_role", "within_km"}
    assert asked["messages"][0]["content"][0]["text"].endswith(
        "<request>Easter near Noosa</request>"
    )


def test_converse_without_a_reading_is_unavailable() -> None:
    with pytest.raises(ReaderUnavailable):
        converse(answered({"text": "Happy camping!"}, stop="end_turn"))


def test_converse_with_a_reading_that_does_not_fit_is_unavailable() -> None:
    bad = {"toolUse": {"toolUseId": "t1", "name": "reading", "input": {"arrive": "soon"}}}
    with pytest.raises(ReaderUnavailable):
        converse(answered(bad))


def test_converse_errors_are_unavailable() -> None:
    denied = ClientError({"Error": {"Code": "AccessDeniedException", "Message": "no"}}, "Converse")
    with pytest.raises(ReaderUnavailable):
        converse(denied)
