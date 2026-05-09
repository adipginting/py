"""Tests for AssistantMessage."""

from py_coding_agent.domain.message import AssistantMessage
from py_coding_agent.domain.message_id import MessageId
from py_coding_agent.domain.tool_call import ToolCall
from py_coding_agent.domain.tool_call_id import ToolCallId


def test_assistant_message_has_text_content() -> None:
    """An assistant message stores text and has role 'assistant'."""
    message = AssistantMessage(text="Hello, user")

    assert message.role == "assistant"
    assert message.text == "Hello, user"
    assert message.tool_calls == ()
    assert isinstance(message.id, MessageId)


def test_assistant_message_can_include_tool_calls() -> None:
    """An assistant message may request one or more tool calls."""
    tool_call = ToolCall(
        id=ToolCallId.from_string("550e8400-e29b-41d4-a716-446655440000"),
        name="read",
        arguments={"path": "/etc/hosts"},
    )

    message = AssistantMessage(text="", tool_calls=(tool_call,))

    assert message.tool_calls == (tool_call,)
    assert message.tool_calls[0].name == "read"
