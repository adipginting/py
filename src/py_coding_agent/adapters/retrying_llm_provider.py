"""RetryingLLMProvider adapter: wraps an LLMProvider with retry logic."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import httpx

from py_coding_agent.domain.message import Message
from py_coding_agent.domain.tool_definition import ToolDefinition
from py_coding_agent.ports.llm_provider import LLMProvider, StreamEvent


def _is_retryable(exc: Exception) -> bool:
    """Determine whether an exception warrants a retry.

    Retries are performed for network-level failures and 5xx server errors.
    4xx client errors are not retried.
    """
    if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False


class RetryingLLMProvider:
    """Wrap an LLMProvider with exponential-backoff retry logic.

    Retries apply to the initial stream connection. Once the stream has
    started yielding events, errors are passed through without retry.
    """

    def __init__(
        self,
        inner: LLMProvider,
        *,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ) -> None:
        self._inner = inner
        self._max_retries = max_retries
        self._base_delay = base_delay

    async def stream(
        self,
        *,
        model: str,
        messages: list[Message],
        tools: list[ToolDefinition],
        system_prompt: str,
    ) -> AsyncIterator[StreamEvent]:
        """Stream completion events with retry on transient failures.

        Args:
            model: The provider-qualified model ID.
            messages: The conversation history.
            tools: Available tools for the assistant.
            system_prompt: The system prompt to prepend.

        Yields:
            StreamEvent from the inner provider.

        Raises:
            Exception: The last exception encountered if all retries are exhausted.
        """
        last_exception: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                inner_iter = self._inner.stream(
                    model=model,
                    messages=messages,
                    tools=tools,
                    system_prompt=system_prompt,
                )
                async for event in inner_iter:
                    yield event
                return
            except Exception as exc:
                last_exception = exc
                if not _is_retryable(exc) or attempt >= self._max_retries:
                    raise
                delay = self._base_delay * (2 ** attempt)
                await asyncio.sleep(delay)

        if last_exception is not None:
            raise last_exception
