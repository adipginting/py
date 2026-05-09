"""Tests for UserMessage."""

from py_coding_agent.domain.message import UserMessage
from py_coding_agent.domain.message_id import MessageId


def test_user_message_has_text_content() -> None:
    """A user message stores text and a unique id."""
    message = UserMessage(text="Hello, agent")

    assert message.role == "user"
    assert message.text == "Hello, agent"
    assert isinstance(message.id, MessageId)
