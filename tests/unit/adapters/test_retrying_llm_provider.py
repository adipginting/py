"""Tests for RetryingLLMProvider adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest

from py_coding_agent.adapters.retrying_llm_provider import RetryingLLMProvider
from py_coding_agent.domain.message import Message, UserMessage
from py_coding_agent.domain.tool_definition import ToolDefinition
from py_coding_agent.ports.llm_provider import StopEvent, StreamEvent, TextChunk


class FlakyProvider:
    """Fake provider that fails a configurable number of times before succeeding."""

    def __init__(self, fail_count: int = 0, exception: Exception | None = None) -> None:
        self.fail_count = fail_count
        self.exception = exception or httpx.ConnectError("Connection refused")
        self.attempts = 0

    async def stream(
        self,
        *,
        model: str,
        messages: list[Message],
        tools: list[ToolDefinition],
        system_prompt: str,
    ) -> AsyncIterator[StreamEvent]:
        self.attempts += 1
        if self.attempts <= self.fail_count:
            raise self.exception
        yield TextChunk(text="Success")
        yield StopEvent(reason="stop")


@pytest.mark.anyio
async def test_retrying_provider_succeeds_on_first_attempt() -> None:
    """When the inner provider succeeds immediately, retry is transparent."""
    inner = FlakyProvider(fail_count=0)
    wrapper = RetryingLLMProvider(inner, max_retries=3, base_delay=0.0)

    events = [e async for e in wrapper.stream(
        model="test",
        messages=[UserMessage(text="Hello")],
        tools=[],
        system_prompt="",
    )]

    assert inner.attempts == 1
    assert len(events) == 2
    assert isinstance(events[0], TextChunk)
    assert events[0].text == "Success"


@pytest.mark.anyio
async def test_retrying_provider_retries_on_transient_failure() -> None:
    """The wrapper retries transient errors and eventually succeeds."""
    inner = FlakyProvider(fail_count=2, exception=httpx.ConnectError(" refused"))
    wrapper = RetryingLLMProvider(inner, max_retries=3, base_delay=0.0)

    events = [e async for e in wrapper.stream(
        model="test",
        messages=[UserMessage(text="Hello")],
        tools=[],
        system_prompt="",
    )]

    assert inner.attempts == 3
    assert len(events) == 2
    assert isinstance(events[0], TextChunk)
    assert events[0].text == "Success"


@pytest.mark.anyio
async def test_retrying_provider_raises_after_max_retries() -> None:
    """When failures exceed max_retries, the last exception is raised."""
    inner = FlakyProvider(fail_count=5, exception=httpx.ConnectError("refused"))
    wrapper = RetryingLLMProvider(inner, max_retries=2, base_delay=0.0)

    with pytest.raises(httpx.ConnectError):
        async for _ in wrapper.stream(
            model="test",
            messages=[UserMessage(text="Hello")],
            tools=[],
            system_prompt="",
        ):
            pass

    assert inner.attempts == 3


@pytest.mark.anyio
async def test_retrying_provider_does_not_retry_on_4xx() -> None:
    """HTTP 4xx client errors are not retried."""
    response = httpx.Response(400, text="Bad Request")
    inner = FlakyProvider(fail_count=5, exception=httpx.HTTPStatusError(
        "Bad Request", request=httpx.Request("POST", "http://test"), response=response
    ))
    wrapper = RetryingLLMProvider(inner, max_retries=3, base_delay=0.0)

    with pytest.raises(httpx.HTTPStatusError):
        async for _ in wrapper.stream(
            model="test",
            messages=[UserMessage(text="Hello")],
            tools=[],
            system_prompt="",
        ):
            pass

    assert inner.attempts == 1


@pytest.mark.anyio
async def test_retrying_provider_retries_on_5xx() -> None:
    """HTTP 5xx server errors are retried."""
    response = httpx.Response(503, text="Service Unavailable")
    inner = FlakyProvider(fail_count=1, exception=httpx.HTTPStatusError(
        "Service Unavailable", request=httpx.Request("POST", "http://test"), response=response
    ))
    wrapper = RetryingLLMProvider(inner, max_retries=3, base_delay=0.0)

    events = [e async for e in wrapper.stream(
        model="test",
        messages=[UserMessage(text="Hello")],
        tools=[],
        system_prompt="",
    )]

    assert inner.attempts == 2
    assert isinstance(events[0], TextChunk)
    assert events[0].text == "Success"


@pytest.mark.anyio
async def test_retrying_provider_delays_between_attempts() -> None:
    """Each retry waits with exponential backoff."""
    inner = FlakyProvider(fail_count=2)
    wrapper = RetryingLLMProvider(inner, max_retries=3, base_delay=0.01)

    events = [e async for e in wrapper.stream(
        model="test",
        messages=[UserMessage(text="Hello")],
        tools=[],
        system_prompt="",
    )]

    assert inner.attempts == 3
    assert isinstance(events[0], TextChunk)
    assert events[0].text == "Success"
