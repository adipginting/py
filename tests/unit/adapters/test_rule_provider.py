"""Tests for RuleProvider."""

import pytest

from py_coding_agent.adapters.rule_provider import RuleProvider
from py_coding_agent.domain.message import ToolResultMessage, UserMessage
from py_coding_agent.domain.tool_call import ToolCall
from py_coding_agent.domain.tool_call_id import ToolCallId
from py_coding_agent.ports.llm_provider import StopEvent, TextChunk, ToolCallChunk


@pytest.mark.anyio
async def test_rule_provider_parses_read_command() -> None:
    """A user message starting with 'read:' triggers a read tool call."""
    provider = RuleProvider()

    events = [
        event async for event in provider.stream(
            model="rule",
            messages=[UserMessage(text="read:/etc/hosts")],
            tools=[],
            system_prompt="",
        )
    ]

    assert len(events) == 2
    assert isinstance(events[0], ToolCallChunk)
    assert events[0].tool_call.name == "read"
    assert events[0].tool_call.arguments["path"] == "/etc/hosts"
    assert isinstance(events[1], StopEvent)
    assert events[1].reason == "tool_calls"


@pytest.mark.anyio
async def test_rule_provider_parses_bash_command() -> None:
    """A user message starting with 'bash:' triggers a bash tool call."""
    provider = RuleProvider()

    events = [
        event async for event in provider.stream(
            model="rule",
            messages=[UserMessage(text="bash:pwd")],
            tools=[],
            system_prompt="",
        )
    ]

    assert isinstance(events[0], ToolCallChunk)
    assert events[0].tool_call.name == "bash"
    assert events[0].tool_call.arguments["command"] == "pwd"


@pytest.mark.anyio
async def test_rule_provider_confirms_tool_results() -> None:
    """When the last message is a tool result, confirm completion."""
    provider = RuleProvider()
    tool_call_id = ToolCallId.from_string("550e8400-e29b-41d4-a716-446655440000")

    events = [
        event async for event in provider.stream(
            model="rule",
            messages=[
                UserMessage(text="bash:pwd"),
                ToolResultMessage(
                    tool_call_id=tool_call_id,
                    content="/home/user",
                ),
            ],
            tools=[],
            system_prompt="",
        )
    ]

    assert len(events) == 2
    assert isinstance(events[0], TextChunk)
    assert "Done" in events[0].text
    assert isinstance(events[1], StopEvent)
    assert events[1].reason == "stop"


@pytest.mark.anyio
async def test_rule_provider_echoes_plain_text() -> None:
    """For unrecognized input, echo the message back."""
    provider = RuleProvider()

    events = [
        event async for event in provider.stream(
            model="rule",
            messages=[UserMessage(text="Just a chat message")],
            tools=[],
            system_prompt="",
        )
    ]

    assert isinstance(events[0], TextChunk)
    assert "Just a chat message" in events[0].text
    assert isinstance(events[1], StopEvent)
