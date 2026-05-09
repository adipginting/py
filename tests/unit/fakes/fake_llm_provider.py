"""Fake LLMProvider for testing use cases without real API calls."""

from __future__ import annotations

from collections.abc import AsyncIterator

from py_coding_agent.domain.message import Message
from py_coding_agent.domain.tool_definition import ToolDefinition
from py_coding_agent.ports.llm_provider import StreamEvent, StreamInvocation


class FakeLLMProvider:
    """A programmable fake LLM provider for unit tests.

    Yields the events given to it. Records each stream invocation
    so tests can verify call parameters.
    """

    def __init__(self, events: list[StreamEvent] | None = None) -> None:
        self.events = events or []
        self.invocations: list[StreamInvocation] = []

    async def stream(
        self,
        *,
        model: str,
        messages: list[Message],
        tools: list[ToolDefinition],
        system_prompt: str,
    ) -> AsyncIterator[StreamEvent]:
        """Yield programmed events and record the invocation."""
        self.invocations.append(
            StreamInvocation(
                model=model,
                messages=messages,
                tools=tools,
                system_prompt=system_prompt,
            )
        )
        for event in self.events:
            yield event
