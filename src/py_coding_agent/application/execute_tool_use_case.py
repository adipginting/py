"""ExecuteToolUseCase: run a single tool call and append the result."""

from __future__ import annotations

from dataclasses import dataclass

from py_coding_agent.domain.agent_state import AgentState
from py_coding_agent.domain.events import DomainEvent
from py_coding_agent.domain.message import AssistantMessage, ToolResultMessage
from py_coding_agent.domain.tool_call import ToolCall
from py_coding_agent.domain.tool_call_id import ToolCallId
from py_coding_agent.ports.tool_executor import ToolExecutor


@dataclass(frozen=True)
class ExecuteToolResult:
    """Result of executing a tool call."""

    tool_result: ToolResultMessage
    events: list[DomainEvent]


class ExecuteToolUseCase:
    """Execute a pending tool call and append the result to state."""

    def __init__(self, tool_executor: ToolExecutor) -> None:
        self._executor = tool_executor

    async def execute(
        self,
        *,
        state: AgentState,
        tool_call_id: ToolCallId,
    ) -> ExecuteToolResult:
        """Execute a single tool call and append its result.

        1. Find the ToolCall in the last assistant message.
        2. Execute via the tool executor.
        3. Append ToolResultMessage to state.
        4. Return the result and domain events.
        """
        tool_call = self._find_tool_call(state, tool_call_id)
        execution_result = await self._executor.execute(tool_call)

        tool_result = ToolResultMessage(
            tool_call_id=tool_call_id,
            content=execution_result.content,
            is_error=execution_result.is_error,
        )

        events = state.append_tool_result(tool_result)
        return ExecuteToolResult(tool_result=tool_result, events=events)

    def _find_tool_call(self, state: AgentState, tool_call_id: ToolCallId) -> ToolCall:
        """Locate the ToolCall matching the given id in the last assistant message."""
        for msg in reversed(state.messages):
            if isinstance(msg, AssistantMessage):
                for tc in msg.tool_calls:
                    if tc.id == tool_call_id:
                        return tc
        raise ValueError(f"Tool call {tool_call_id} not found in conversation")
