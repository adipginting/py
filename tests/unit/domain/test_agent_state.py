"""Tests for AgentState aggregate root."""

import pytest

from py_coding_agent.domain.agent_state import AgentState
from py_coding_agent.domain.message import (
    AssistantMessage,
    ToolResultMessage,
    UserMessage,
)
from py_coding_agent.domain.tool_call import ToolCall
from py_coding_agent.domain.tool_call_id import ToolCallId


def test_agent_state_starts_empty() -> None:
    """A newly created AgentState has no messages."""
    state = AgentState()

    assert state.messages == []
    assert state.pending_tool_call_ids == set()


def test_appending_user_message_increases_messages() -> None:
    """Adding a user message appends it to the message list."""
    state = AgentState()
    message = UserMessage(text="Hello")

    state.append_user_message(message)

    assert state.messages == [message]


def test_appending_assistant_message_tracks_tool_calls() -> None:
    """When an assistant message includes tool calls, they become pending."""
    state = AgentState()
    tool_call_id = ToolCallId.from_string("550e8400-e29b-41d4-a716-446655440000")
    tool_call = ToolCall(
        id=tool_call_id,
        name="read",
        arguments={"path": "/etc/hosts"},
    )
    message = AssistantMessage(text="", tool_calls=(tool_call,))

    state.append_assistant_message(message)

    assert state.messages == [message]
    assert state.pending_tool_call_ids == {tool_call_id}


def test_appending_tool_result_clears_pending_tool_call() -> None:
    """A tool result for a pending tool call removes it from pending."""
    state = AgentState()
    tool_call_id = ToolCallId.from_string("550e8400-e29b-41d4-a716-446655440000")
    tool_call = ToolCall(
        id=tool_call_id,
        name="read",
        arguments={"path": "/etc/hosts"},
    )
    state.append_assistant_message(AssistantMessage(text="", tool_calls=(tool_call,)))

    result = ToolResultMessage(tool_call_id=tool_call_id, content="127.0.0.1 localhost")
    state.append_tool_result(result)

    assert state.messages[-1] == result
    assert state.pending_tool_call_ids == set()


def test_appending_tool_result_for_unknown_tool_call_raises() -> None:
    """A tool result for a tool call that was not requested is an invariant violation."""
    state = AgentState()
    tool_call_id = ToolCallId.from_string("550e8400-e29b-41d4-a716-446655440000")
    result = ToolResultMessage(tool_call_id=tool_call_id, content="oops")

    with pytest.raises(ValueError, match="No pending tool call"):
        state.append_tool_result(result)


def test_appending_assistant_message_without_tool_calls_clears_pending() -> None:
    """A follow-up assistant message with no tool calls leaves no pending calls."""
    state = AgentState()
    tool_call_id = ToolCallId.from_string("550e8400-e29b-41d4-a716-446655440000")
    tool_call = ToolCall(
        id=tool_call_id,
        name="read",
        arguments={"path": "/etc/hosts"},
    )
    state.append_assistant_message(AssistantMessage(text="", tool_calls=(tool_call,)))
    state.append_tool_result(ToolResultMessage(tool_call_id=tool_call_id, content="done"))

    state.append_assistant_message(AssistantMessage(text="All done"))

    assert state.pending_tool_call_ids == set()
