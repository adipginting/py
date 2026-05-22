"""Tests for ExecuteToolUseCase."""

import pytest

from py_coding_agent.application.execute_tool_use_case import ExecuteToolUseCase
from py_coding_agent.domain.agent_state import AgentState
from py_coding_agent.domain.events import ToolResultAppended
from py_coding_agent.domain.message import AssistantMessage, ToolResultMessage
from py_coding_agent.domain.tool_call import ToolCall
from py_coding_agent.domain.tool_call_id import ToolCallId
from py_coding_agent.ports.tool_executor import ToolExecutionResult
from tests.unit.fakes.fake_tool_executor import FakeToolExecutor


@pytest.mark.anyio
async def test_execute_tool_appends_result() -> None:
    """A tool call is executed and its result appended to state."""
    fake = FakeToolExecutor(results={"read": ToolExecutionResult(content="hello")})
    use_case = ExecuteToolUseCase(tool_executor=fake)
    state = AgentState()
    tool_call_id = ToolCallId.from_string("550e8400-e29b-41d4-a716-446655440000")
    state.append_assistant_message(
        AssistantMessage(
            text="",
            tool_calls=(ToolCall(id=tool_call_id, name="read", arguments={"path": "/etc/hosts"}),),
        )
    )

    result = await use_case.execute(state=state, tool_call_id=tool_call_id)

    assert isinstance(state.messages[-1], ToolResultMessage)
    assert state.messages[-1].content == "hello"
    assert state.messages[-1].tool_call_id == tool_call_id
    assert result.tool_result.content == "hello"


@pytest.mark.anyio
async def test_execute_tool_returns_events() -> None:
    """The use case returns domain events from appending the result."""
    fake = FakeToolExecutor(results={"read": ToolExecutionResult(content="done")})
    use_case = ExecuteToolUseCase(tool_executor=fake)
    state = AgentState()
    tool_call_id = ToolCallId.from_string("550e8400-e29b-41d4-a716-446655440000")
    state.append_assistant_message(
        AssistantMessage(
            text="",
            tool_calls=(ToolCall(id=tool_call_id, name="read", arguments={}),),
        )
    )

    result = await use_case.execute(state=state, tool_call_id=tool_call_id)

    assert any(isinstance(e, ToolResultAppended) for e in result.events)


@pytest.mark.anyio
async def test_execute_tool_with_error() -> None:
    """A tool that returns an error is appended with is_error=True."""
    fake = FakeToolExecutor(
        results={"read": ToolExecutionResult(content="not found", is_error=True)}
    )
    use_case = ExecuteToolUseCase(tool_executor=fake)
    state = AgentState()
    tool_call_id = ToolCallId.from_string("550e8400-e29b-41d4-a716-446655440001")
    state.append_assistant_message(
        AssistantMessage(
            text="",
            tool_calls=(ToolCall(id=tool_call_id, name="read", arguments={}),),
        )
    )

    await use_case.execute(state=state, tool_call_id=tool_call_id)

    assert state.messages[-1].is_error is True
    assert state.messages[-1].content == "not found"
