"""LLMProvider port: the outbound interface for streaming LLM completions."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from py_coding_agent.domain.message import Message
    from py_coding_agent.domain.tool_call import ToolCall
    from py_coding_agent.domain.tool_definition import ToolDefinition


@dataclass(frozen=True)
class StreamEvent:
    """Base class for all stream events from an LLM."""

    pass


@dataclass(frozen=True)
class TextChunk(StreamEvent):
    """A fragment of text from the assistant's response."""

    text: str


@dataclass(frozen=True)
class ToolCallChunk(StreamEvent):
    """The assistant has requested a tool call."""

    tool_call: ToolCall


@dataclass(frozen=True)
class ThinkingChunk(StreamEvent):
    """A fragment of the assistant's reasoning/thinking."""

    text: str


@dataclass(frozen=True)
class UsageEvent(StreamEvent):
    """Token usage metadata delivered at the end of a stream."""

    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class StopEvent(StreamEvent):
    """The stream has ended."""

    reason: str


@dataclass(frozen=True)
class StreamInvocation:
    """A record of a single stream call for testing."""

    model: str
    messages: list[Message]
    tools: list[ToolDefinition]
    system_prompt: str


class LLMProvider(Protocol):
    """Outbound port for streaming LLM completions.

    Implementations handle the specifics of each provider's API,
    normalizing them into a uniform stream of domain events.
    """

    def stream(
        self,
        *,
        model: str,
        messages: list[Message],
        tools: list[ToolDefinition],
        system_prompt: str,
    ) -> AsyncIterator[StreamEvent]:
        """Begin a streaming completion.

        Args:
            model: The provider-qualified model ID (e.g., "openai/gpt-4o").
            messages: The conversation history, ending with the latest user message.
            tools: The tools available to the assistant in this turn.
            system_prompt: The system prompt to prepend.

        Yields:
            StreamEvent: Text chunks, tool calls, thinking, usage, and stop events.
        """
        ...
