"""Tests for EchoProvider adapter."""

import pytest

from py_coding_agent.adapters.echo_provider import EchoProvider
from py_coding_agent.domain.message import UserMessage
from py_coding_agent.ports.llm_provider import StopEvent, TextChunk


@pytest.mark.anyio
async def test_echo_provider_repeats_user_message() -> None:
    """EchoProvider returns the user's last message text as the assistant response."""
    provider = EchoProvider()

    events = []
    async for event in provider.stream(
        model="echo",
        messages=[UserMessage(text="Hello")],
        tools=[],
        system_prompt="",
    ):
        events.append(event)

    assert len(events) == 2
    assert isinstance(events[0], TextChunk)
    assert events[0].text == "Echo: Hello"
    assert isinstance(events[1], StopEvent)
    assert events[1].reason == "stop"


@pytest.mark.anyio
async def test_echo_provider_responds_to_last_user_message() -> None:
    """EchoProvider reads the last user message from the conversation history."""
    provider = EchoProvider()

    events = []
    async for event in provider.stream(
        model="echo",
        messages=[
            UserMessage(text="First"),
            UserMessage(text="Second"),
        ],
        tools=[],
        system_prompt="",
    ):
        events.append(event)

    assert events[0].text == "Echo: Second"
