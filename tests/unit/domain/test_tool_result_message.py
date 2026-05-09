"""Tests for ToolResultMessage."""

from py_coding_agent.domain.message import ToolResultMessage
from py_coding_agent.domain.message_id import MessageId
from py_coding_agent.domain.tool_call_id import ToolCallId


def test_tool_result_message_links_to_tool_call() -> None:
    """A tool result message references the tool call it answers."""
    tool_call_id = ToolCallId.from_string("550e8400-e29b-41d4-a716-446655440000")
    message = ToolResultMessage(
        tool_call_id=tool_call_id,
        content="127.0.0.1 localhost",
    )

    assert message.role == "tool"
    assert message.tool_call_id == tool_call_id
    assert message.content == "127.0.0.1 localhost"
    assert isinstance(message.id, MessageId)


def test_tool_result_message_can_carry_error() -> None:
    """A tool result may indicate an error instead of normal content."""
    tool_call_id = ToolCallId.from_string("550e8400-e29b-41d4-a716-446655440001")
    message = ToolResultMessage(
        tool_call_id=tool_call_id,
        content="File not found",
        is_error=True,
    )

    assert message.is_error is True
