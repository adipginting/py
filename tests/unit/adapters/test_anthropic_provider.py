"""Tests for AnthropicProvider adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, cast

import httpx
import pytest

from py_coding_agent.adapters.anthropic_provider import AnthropicProvider, _parse_anthropic_sse
from py_coding_agent.domain.message import AssistantMessage, ToolResultMessage, UserMessage
from py_coding_agent.domain.tool_call import ToolCall
from py_coding_agent.domain.tool_call_id import ToolCallId
from py_coding_agent.domain.tool_definition import ToolDefinition
from py_coding_agent.ports.llm_provider import (
    StopEvent,
    StreamEvent,
    TextChunk,
    ToolCallChunk,
    UsageEvent,
)


async def _lines(*items: str) -> AsyncIterator[str]:
    for item in items:
        yield item


@pytest.mark.anyio
async def test_parse_sse_yields_text_chunks() -> None:
    """Anthropic text deltas are yielded as TextChunk events."""
    lines = _lines(
        "event: message_start",
        'data: {"type":"message_start","message":{"id":"msg_01","usage":{"input_tokens":10,"output_tokens":0}}}',
        "",
        "event: content_block_start",
        'data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}',
        "",
        "event: content_block_delta",
        'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}',
        "",
        "event: content_block_delta",
        'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":" world"}}',
        "",
        "event: content_block_stop",
        'data: {"type":"content_block_stop","index":0}',
        "",
        "event: message_delta",
        'data: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":2}}',
        "",
        "event: message_stop",
        'data: {"type":"message_stop"}',
        "",
    )

    events = [e async for e in _parse_anthropic_sse(lines)]

    assert len(events) == 4
    assert isinstance(events[0], TextChunk)
    assert events[0].text == "Hello"
    assert isinstance(events[1], TextChunk)
    assert events[1].text == " world"
    assert isinstance(events[2], UsageEvent)
    assert events[2].input_tokens == 10
    assert events[2].output_tokens == 2
    assert isinstance(events[3], StopEvent)
    assert events[3].reason == "end_turn"


@pytest.mark.anyio
async def test_parse_sse_yields_tool_call() -> None:
    """Anthropic tool_use blocks are yielded as ToolCallChunk."""
    lines = _lines(
        "event: message_start",
        'data: {"type":"message_start","message":{"id":"msg_01","usage":{"input_tokens":5,"output_tokens":0}}}',
        "",
        "event: content_block_start",
        'data: {"type":"content_block_start","index":0,"content_block":{"type":"tool_use","id":"tu_01","name":"bash","input":{}}}',
        "",
        "event: content_block_delta",
        'data: {"type":"content_block_delta","index":0,"delta":{"type":"input_json_delta","partial_json":"{\\"command\\": \\"ls\\"}"}}',
        "",
        "event: content_block_stop",
        'data: {"type":"content_block_stop","index":0}',
        "",
        "event: message_delta",
        'data: {"type":"message_delta","delta":{"stop_reason":"tool_use"}}',
        "",
        "event: message_stop",
        'data: {"type":"message_stop"}',
        "",
    )

    events = [e async for e in _parse_anthropic_sse(lines)]

    assert len(events) == 3
    assert isinstance(events[0], ToolCallChunk)
    assert events[0].tool_call.name == "bash"
    assert events[0].tool_call.arguments == {"command": "ls"}
    assert isinstance(events[1], UsageEvent)
    assert events[1].input_tokens == 5
    assert events[1].output_tokens == 0
    assert isinstance(events[2], StopEvent)
    assert events[2].reason == "tool_use"


@pytest.mark.anyio
async def test_parse_sse_ignores_ping_lines() -> None:
    """Blank lines and unknown events are ignored."""
    lines = _lines(
        "event: message_start",
        'data: {"type":"message_start","message":{"id":"msg_01","usage":{"input_tokens":1,"output_tokens":0}}}',
        "",
        "event: content_block_start",
        'data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}',
        "",
        "",
        "event: content_block_delta",
        'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"x"}}',
        "",
        "event: message_stop",
        'data: {"type":"message_stop"}',
        "",
    )

    events = [e async for e in _parse_anthropic_sse(lines)]

    assert len(events) == 2
    assert isinstance(events[0], TextChunk)
    assert events[0].text == "x"


class FakeHttpClient:
    """Hand-written fake for httpx.AsyncClient."""

    def __init__(self, lines: list[str]) -> None:
        self.lines = lines
        self.requests: list[dict[str, Any]] = []

    async def post(
        self, url: str, *, headers: dict[str, Any] | None = None, json: dict[str, Any] | None = None
    ) -> FakeResponse:
        self.requests.append({"url": url, "headers": headers, "json": json})
        return FakeResponse(self.lines)

    async def aclose(self) -> None:
        pass


class FakeResponse:
    """Fake httpx.Response that yields SSE lines."""

    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    async def aiter_lines(self) -> AsyncIterator[str]:
        for line in self._lines:
            yield line

    async def aclose(self) -> None:
        pass

    def raise_for_status(self) -> None:
        pass


@pytest.mark.anyio
async def test_anthropic_provider_sends_correct_request() -> None:
    """AnthropicProvider translates domain objects into the Anthropic request format."""
    fake_client = FakeHttpClient(
        [
            "event: message_start",
            'data: {"type":"message_start","message":{"id":"msg_01","usage":{"input_tokens":10,"output_tokens":0}}}',
            "",
            "event: content_block_delta",
            'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hi"}}',
            "",
            "event: message_stop",
            'data: {"type":"message_stop"}',
            "",
        ]
    )
    provider = AnthropicProvider(api_key="sk-test", http_client=cast(httpx.AsyncClient, fake_client))

    events: list[StreamEvent] = []
    async for event in provider.stream(
        model="claude-sonnet-4-20250514",
        messages=[UserMessage(text="Hello")],
        tools=[],
        system_prompt="You are a test assistant.",
    ):
        events.append(event)

    assert len(fake_client.requests) == 1
    req = fake_client.requests[0]
    assert req["url"] == "https://api.anthropic.com/v1/messages"
    assert req["headers"]["x-api-key"] == "sk-test"
    assert req["headers"]["anthropic-version"] == "2023-06-01"
    body = req["json"]
    assert body["model"] == "claude-sonnet-4-20250514"
    assert body["stream"] is True
    assert body["max_tokens"] == 4096
    assert body["system"] == "You are a test assistant."
    assert body["messages"] == [{"role": "user", "content": [{"type": "text", "text": "Hello"}]}]


@pytest.mark.anyio
async def test_anthropic_provider_converts_tool_definitions() -> None:
    """ToolDefinition objects are serialized into Anthropic tool schema."""
    fake_client = FakeHttpClient(
        [
            "event: message_stop",
            'data: {"type":"message_stop"}',
            "",
        ]
    )
    provider = AnthropicProvider(api_key="sk-test", http_client=cast(httpx.AsyncClient, fake_client))

    tool = ToolDefinition(
        name="bash",
        description="Run shell commands",
        parameters={"command": {"type": "string"}},
    )

    async for _ in provider.stream(
        model="claude-sonnet-4-20250514",
        messages=[UserMessage(text="Run ls")],
        tools=[tool],
        system_prompt="",
    ):
        pass

    body = fake_client.requests[0]["json"]
    assert body["tools"] == [
        {
            "name": "bash",
            "description": "Run shell commands",
            "input_schema": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
            },
        }
    ]


@pytest.mark.anyio
async def test_anthropic_provider_converts_assistant_message_with_tool_calls() -> None:
    """Assistant messages containing tool_use are serialized correctly."""
    fake_client = FakeHttpClient(
        [
            "event: message_stop",
            'data: {"type":"message_stop"}',
            "",
        ]
    )
    provider = AnthropicProvider(api_key="sk-test", http_client=cast(httpx.AsyncClient, fake_client))

    assistant = AssistantMessage(
        text="",
        tool_calls=(
            ToolCall(
                id=ToolCallId.from_string("tu_01"),
                name="bash",
                arguments={"command": "ls"},
            ),
        ),
    )

    async for _ in provider.stream(
        model="claude-sonnet-4-20250514",
        messages=[assistant],
        tools=[],
        system_prompt="",
    ):
        pass

    body = fake_client.requests[0]["json"]
    assert body["messages"] == [
        {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "tu_01",
                    "name": "bash",
                    "input": {"command": "ls"},
                }
            ],
        }
    ]


@pytest.mark.anyio
async def test_anthropic_provider_converts_tool_result_message() -> None:
    """ToolResultMessage is serialized as a tool_result content block."""
    fake_client = FakeHttpClient(
        [
            "event: message_stop",
            'data: {"type":"message_stop"}',
            "",
        ]
    )
    provider = AnthropicProvider(api_key="sk-test", http_client=cast(httpx.AsyncClient, fake_client))

    result = ToolResultMessage(
        tool_call_id=ToolCallId.from_string("tu_01"),
        content="file.txt",
    )

    async for _ in provider.stream(
        model="claude-sonnet-4-20250514",
        messages=[result],
        tools=[],
        system_prompt="",
    ):
        pass

    body = fake_client.requests[0]["json"]
    assert body["messages"] == [
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "tu_01",
                    "content": "file.txt",
                    "is_error": False,
                }
            ],
        }
    ]
