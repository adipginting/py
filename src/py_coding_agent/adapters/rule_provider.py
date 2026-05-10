"""RuleProvider adapter: deterministic rule-based LLM for demos."""

from collections.abc import AsyncIterator

from py_coding_agent.domain.message import Message, ToolResultMessage, UserMessage
from py_coding_agent.domain.tool_call import ToolCall
from py_coding_agent.domain.tool_call_id import ToolCallId
from py_coding_agent.domain.tool_definition import ToolDefinition
from py_coding_agent.ports.llm_provider import (
    StopEvent,
    StreamEvent,
    TextChunk,
    ToolCallChunk,
)


class RuleProvider:
    """Deterministic rule-based provider that parses user messages for commands.

    Recognized patterns:
      - "bash:<command>"  → bash tool call
      - "read:<path>"     → read tool call
      - "write:<path>:<content>" → write tool call
      - plain text        → echo back
      - tool result seen  → confirm completion
    """

    async def stream(
        self,
        *,
        model: str,
        messages: list[Message],
        tools: list[ToolDefinition],
        system_prompt: str,
    ) -> AsyncIterator[StreamEvent]:
        """Yield events based on simple rules."""
        if not messages:
            yield TextChunk(text="No message to process.")
            yield StopEvent(reason="stop")
            return

        last = messages[-1]

        if isinstance(last, ToolResultMessage):
            yield TextChunk(text=f"Done. Result: {last.content}")
            yield StopEvent(reason="stop")
            return

        if isinstance(last, UserMessage):
            text = last.text.strip()

            if text.startswith("bash:"):
                command = text[5:].strip()
                yield ToolCallChunk(
                    tool_call=ToolCall(
                        id=ToolCallId(),
                        name="bash",
                        arguments={"command": command},
                    )
                )
                yield StopEvent(reason="tool_calls")
                return

            if text.startswith("read:"):
                path = text[5:].strip()
                yield ToolCallChunk(
                    tool_call=ToolCall(
                        id=ToolCallId(),
                        name="read",
                        arguments={"path": path},
                    )
                )
                yield StopEvent(reason="tool_calls")
                return

            if text.startswith("write:"):
                parts = text[6:].split(":", 1)
                if len(parts) == 2:
                    yield ToolCallChunk(
                        tool_call=ToolCall(
                            id=ToolCallId(),
                            name="write",
                            arguments={"path": parts[0].strip(), "content": parts[1]},
                        )
                    )
                    yield StopEvent(reason="tool_calls")
                    return

            # Default: echo
            yield TextChunk(text=f"Echo: {text}")
            yield StopEvent(reason="stop")
            return

        yield TextChunk(text="Unrecognized message type.")
        yield StopEvent(reason="stop")
