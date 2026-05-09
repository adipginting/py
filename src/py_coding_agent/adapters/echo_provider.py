"""EchoProvider adapter: a trivial LLM provider for testing and demos.

Echoes the user's last message text back as the assistant response.
"""

from collections.abc import AsyncIterator

from py_coding_agent.domain.message import Message, UserMessage
from py_coding_agent.domain.tool_definition import ToolDefinition
from py_coding_agent.ports.llm_provider import StopEvent, StreamEvent, TextChunk


class EchoProvider:
    """Echo the last user message back as the assistant response."""

    async def stream(
        self,
        *,
        model: str,
        messages: list[Message],
        tools: list[ToolDefinition],
        system_prompt: str,
    ) -> AsyncIterator[StreamEvent]:
        """Yield the last user message text as a text chunk."""
        last_text = ""
        for msg in reversed(messages):
            if isinstance(msg, UserMessage):
                last_text = msg.text
                break
        yield TextChunk(text=f"Echo: {last_text}")
        yield StopEvent(reason="stop")
