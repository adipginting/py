"""Tests for domain events emitted by AgentState."""

from py_coding_agent.domain.agent_state import AgentState
from py_coding_agent.domain.events import (
    MessageAppended,
    ToolResultAppended,
)
from py_coding_agent.domain.message import (
    AssistantMessage,
    ToolResultMessage,
    UserMessage,
)
from py_coding_agent.domain.tool_call import ToolCall
from py_coding_agent.domain.tool_call_id import ToolCallId


def test_appending_user_message_emits_message_appended_event() -> None:
    """When a user message is appended, a MessageAppended event is emitted."""
    state = AgentState()
    message = UserMessage(text="Hello")

    events = state.append_user_message(message)

    assert len(events) == 1
    assert isinstance(events[0], MessageAppended)
    assert events[0].message == message


def test_appending_assistant_message_with_tool_call_emits_event() -> None:
    """Appending an assistant message with tool calls emits MessageAppended."""
    state = AgentState()
    tool_call = ToolCall(
        id=ToolCallId.from_string("550e8400-e29b-41d4-a716-446655440000"),
        name="read",
        arguments={},
    )
    message = AssistantMessage(text="", tool_calls=(tool_call,))

    events = state.append_assistant_message(message)

    assert len(events) == 1
    assert isinstance(events[0], MessageAppended)
    assert events[0].message == message


def test_appending_tool_result_emits_tool_result_appended_event() -> None:
    """When a tool result is appended, a ToolResultAppended event is emitted."""
    state = AgentState()
    tool_call_id = ToolCallId.from_string("550e8400-e29b-41d4-a716-446655440000")
    state.append_assistant_message(
        AssistantMessage(text="", tool_calls=(ToolCall(id=tool_call_id, name="read", arguments={}),))
    )
    result = ToolResultMessage(tool_call_id=tool_call_id, content="done")

    events = state.append_tool_result(result)

    assert len(events) == 1
    assert isinstance(events[0], ToolResultAppended)
    assert events[0].message == result


def test_events_are_drained_after_collection() -> None:
    """Once events are returned from an append method, they are not duplicated."""
    state = AgentState()
    state.append_user_message(UserMessage(text="Hello"))

    events = state.collect_events()

    assert len(events) == 0
