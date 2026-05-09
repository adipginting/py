"""PromptUseCase: send a user message and receive an assistant response."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from py_coding_agent.domain.agent_state import AgentState
from py_coding_agent.domain.events import DomainEvent
from py_coding_agent.domain.message import AssistantMessage, UserMessage
from py_coding_agent.domain.tool_call import ToolCall
from py_coding_agent.domain.tool_definition import ToolDefinition

if TYPE_CHECKING:
    from py_coding_agent.ports.llm_provider import (
        LLMProvider,
        StreamEvent,
    )


@dataclass(frozen=True)
class PromptResult:
    """Result of executing PromptUseCase."""

    assistant_message: AssistantMessage
    events: list[DomainEvent]


class PromptUseCase:
    """Send a user message to the LLM and append the response to state."""

    def __init__(self, llm_provider: LLMProvider) -> None:
        self._llm = llm_provider

    async def execute(
        self,
        *,
        state: AgentState,
        text: str,
        model: str = "openai/gpt-4o",
        tools: list[ToolDefinition] | None = None,
        system_prompt: str = "",
    ) -> PromptResult:
        """Execute the prompt workflow.

        1. Append user message to state.
        2. Stream LLM response.
        3. Collect text chunks and tool calls into AssistantMessage.
        4. Append assistant message to state.
        5. Return the assistant message and all domain events.
        """
        events: list[DomainEvent] = []

        # Step 1: append user message
        events.extend(state.append_user_message(UserMessage(text=text)))

        # Step 2: stream from LLM
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        async for event in self._llm.stream(
            model=model,
            messages=state.messages,
            tools=tools or [],
            system_prompt=system_prompt,
        ):
            self._handle_stream_event(event, text_parts, tool_calls)

        # Step 3: build assistant message
        assistant = AssistantMessage(
            text="".join(text_parts),
            tool_calls=tuple(tool_calls),
        )

        # Step 4: append assistant message
        events.extend(state.append_assistant_message(assistant))

        return PromptResult(assistant_message=assistant, events=events)

    def _handle_stream_event(
        self,
        event: StreamEvent,
        text_parts: list[str],
        tool_calls: list[ToolCall],
    ) -> None:
        from py_coding_agent.ports.llm_provider import TextChunk, ToolCallChunk

        if isinstance(event, TextChunk):
            text_parts.append(event.text)
        elif isinstance(event, ToolCallChunk):
            tool_calls.append(event.tool_call)
