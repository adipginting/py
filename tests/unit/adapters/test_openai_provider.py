"""Tests for OpenAIProvider adapter."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any, cast

import httpx
import pytest

from py_coding_agent.adapters.openai_provider import OpenAIProvider, _parse_openai_sse
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
    """SSE text deltas are yielded as TextChunk events."""
    lines = _lines(
        'data: {"choices":[{"delta":{"content":"Hello"}}]}',
        "",
        'data: {"choices":[{"delta":{"content":" world"}}]}',
        "",
        "data: [DONE]",
    )

    events = [e async for e in _parse_openai_sse(lines)]

    assert len(events) == 3
    assert isinstance(events[0], TextChunk)
    assert events[0].text == "Hello"
    assert isinstance(events[1], TextChunk)
    assert events[1].text == " world"
    assert isinstance(events[2], StopEvent)
    assert events[2].reason == "stop"


@pytest.mark.anyio
async def test_parse_sse_yields_tool_call() -> None:
    """Accumulated tool call deltas are yielded as a single ToolCallChunk."""
    lines = _lines(
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_123","type":"function","function":{"name":"bash"}}]}}]}',
        "",
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"{\\"c"}}]}}]}',
        "",
        'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"ommand\\":\\"ls\\"}"}}]}}]}',
        "",
        'data: {"choices":[{"delta":{},"finish_reason":"tool_calls"}]}',
        "",
        "data: [DONE]",
    )

    events = [e async for e in _parse_openai_sse(lines)]

    assert len(events) == 2
    assert isinstance(events[0], ToolCallChunk)
    assert events[0].tool_call.name == "bash"
    assert events[0].tool_call.arguments == {"command": "ls"}
    assert isinstance(events[1], StopEvent)
    assert events[1].reason == "tool_calls"


@pytest.mark.anyio
async def test_parse_sse_yields_usage_event() -> None:
    """When usage appears in a chunk, it is yielded as UsageEvent."""
    lines = _lines(
        'data: {"choices":[{"delta":{"content":"Hi"}}],"usage":{"prompt_tokens":10,"completion_tokens":2}}',
        "",
        "data: [DONE]",
    )

    events = [e async for e in _parse_openai_sse(lines)]

    assert len(events) == 3
    assert isinstance(events[0], TextChunk)
    assert isinstance(events[1], UsageEvent)
    assert events[1].input_tokens == 10
    assert events[1].output_tokens == 2
    assert isinstance(events[2], StopEvent)


@pytest.mark.anyio
async def test_parse_sse_ignores_empty_lines() -> None:
    """Blank lines between SSE events are ignored."""
    lines = _lines(
        "",
        'data: {"choices":[{"delta":{"content":"x"}}]}',
        "",
        "",
        "data: [DONE]",
    )

    events = [e async for e in _parse_openai_sse(lines)]

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
async def test_openai_provider_sends_correct_request() -> None:
    """OpenAIProvider translates domain objects into the OpenAI request format."""
    fake_client = FakeHttpClient(
        [
            'data: {"choices":[{"delta":{"content":"Hi"}}]}',
            "data: [DONE]",
        ]
    )
    provider = OpenAIProvider(api_key="sk-test", http_client=cast(httpx.AsyncClient, fake_client))

    events: list[StreamEvent] = []
    async for event in provider.stream(
        model="gpt-4o",
        messages=[UserMessage(text="Hello")],
        tools=[],
        system_prompt="You are a test assistant.",
    ):
        events.append(event)

    assert len(fake_client.requests) == 1
    req = fake_client.requests[0]
    assert req["url"] == "https://api.openai.com/v1/chat/completions"
    assert req["headers"]["Authorization"] == "Bearer sk-test"
    body = req["json"]
    assert body["model"] == "gpt-4o"
    assert body["stream"] is True
    assert body["messages"] == [
        {"role": "system", "content": "You are a test assistant."},
        {"role": "user", "content": "Hello"},
    ]


@pytest.mark.anyio
async def test_openai_provider_converts_tool_definitions() -> None:
    """ToolDefinition objects are serialized into OpenAI function schema."""
    fake_client = FakeHttpClient(
        [
            'data: {"choices":[{"delta":{"content":"ok"}}]}',
            "data: [DONE]",
        ]
    )
    provider = OpenAIProvider(api_key="sk-test", http_client=cast(httpx.AsyncClient, fake_client))

    tool = ToolDefinition(
        name="bash",
        description="Run shell commands",
        parameters={"command": {"type": "string"}},
    )

    async for _ in provider.stream(
        model="gpt-4o",
        messages=[UserMessage(text="Run ls")],
        tools=[tool],
        system_prompt="",
    ):
        pass

    body = fake_client.requests[0]["json"]
    assert body["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "bash",
                "description": "Run shell commands",
                "parameters": {
                    "type": "object",
                    "properties": {"command": {"type": "string"}},
                },
            },
        }
    ]


@pytest.mark.anyio
async def test_openai_provider_converts_assistant_message_with_tool_calls() -> None:
    """Assistant messages containing tool calls are serialized correctly."""
    fake_client = FakeHttpClient(
        [
            'data: {"choices":[{"delta":{"content":"done"}}]}',
            "data: [DONE]",
        ]
    )
    provider = OpenAIProvider(api_key="sk-test", http_client=cast(httpx.AsyncClient, fake_client))

    assistant = AssistantMessage(
        text="",
        tool_calls=(
            ToolCall(
                id=ToolCallId.from_string("call_123"),
                name="bash",
                arguments={"command": "ls"},
            ),
        ),
    )

    async for _ in provider.stream(
        model="gpt-4o",
        messages=[assistant],
        tools=[],
        system_prompt="",
    ):
        pass

    body = fake_client.requests[0]["json"]
    assert body["messages"] == [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "bash",
                        "arguments": json.dumps({"command": "ls"}),
                    },
                }
            ],
        }
    ]


@pytest.mark.anyio
async def test_openai_provider_converts_tool_result_message() -> None:
    """ToolResultMessage is serialized as a tool message."""
    fake_client = FakeHttpClient(
        [
            'data: {"choices":[{"delta":{"content":"ok"}}]}',
            "data: [DONE]",
        ]
    )
    provider = OpenAIProvider(api_key="sk-test", http_client=cast(httpx.AsyncClient, fake_client))

    result = ToolResultMessage(
        tool_call_id=ToolCallId.from_string("call_123"),
        content="file.txt",
    )

    async for _ in provider.stream(
        model="gpt-4o",
        messages=[result],
        tools=[],
        system_prompt="",
    ):
        pass

    body = fake_client.requests[0]["json"]
    assert body["messages"] == [{"role": "tool", "tool_call_id": "call_123", "content": "file.txt"}]
