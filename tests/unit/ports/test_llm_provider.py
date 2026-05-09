"""Tests for LLMProvider port and FakeLLMProvider."""

from collections.abc import AsyncIterator

import pytest

from py_coding_agent.domain.message import UserMessage
from py_coding_agent.domain.tool_call import ToolCall
from py_coding_agent.domain.tool_call_id import ToolCallId
from py_coding_agent.ports.llm_provider import (
    LLMProvider,
    StopEvent,
    StreamEvent,
    TextChunk,
    ToolCallChunk,
)
from tests.unit.fakes.fake_llm_provider import FakeLLMProvider


async def _consume(iterator: AsyncIterator[StreamEvent]) -> list[StreamEvent]:
    return [event async for event in iterator]


def test_llm_provider_is_implementable() -> None:
    """FakeLLMProvider must satisfy the LLMProvider protocol."""
    fake: LLMProvider = FakeLLMProvider()
    assert fake is not None


@pytest.mark.anyio
async def test_fake_llm_provider_returns_programmed_events() -> None:
    """FakeLLMProvider yields the events programmed into it."""
    tool_call_id = ToolCallId.from_string("550e8400-e29b-41d4-a716-446655440000")
    tool_call = ToolCall(id=tool_call_id, name="read", arguments={"path": "/etc/hosts"})

    fake = FakeLLMProvider(
        events=[
            TextChunk(text="I'll read "),
            TextChunk(text="that file."),
            ToolCallChunk(tool_call=tool_call),
            StopEvent(reason="tool_calls"),
        ]
    )

    events = await _consume(
        fake.stream(
            model="openai/gpt-4o",
            messages=[UserMessage(text="Read /etc/hosts")],
            tools=[],
            system_prompt="You are a helpful assistant.",
        )
    )

    assert len(events) == 4
    assert isinstance(events[0], TextChunk)
    assert events[0].text == "I'll read "
    assert isinstance(events[2], ToolCallChunk)
    assert events[2].tool_call.name == "read"
    assert isinstance(events[3], StopEvent)
    assert events[3].reason == "tool_calls"


@pytest.mark.anyio
async def test_fake_llm_provider_records_invocations() -> None:
    """FakeLLMProvider records each stream call for later inspection."""
    fake = FakeLLMProvider(events=[TextChunk(text="Hi")])

    await _consume(fake.stream(model="anthropic/claude", messages=[UserMessage(text="Hello")], tools=[], system_prompt=""))

    assert len(fake.invocations) == 1
    assert fake.invocations[0].model == "anthropic/claude"
    assert fake.invocations[0].messages[0].text == "Hello"
