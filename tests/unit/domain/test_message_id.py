"""Tests for MessageId value object."""

from uuid import UUID

from py_coding_agent.domain.message_id import MessageId


def test_message_id_generates_valid_uuid_by_default() -> None:
    """Creating a MessageId without arguments yields a valid UUID."""
    message_id = MessageId()

    assert isinstance(message_id.value, UUID)


def test_message_id_can_be_created_from_uuid_string() -> None:
    """A MessageId can be constructed from a UUID string."""
    raw = "550e8400-e29b-41d4-a716-446655440000"

    message_id = MessageId.from_string(raw)

    assert str(message_id.value) == raw


def test_equal_message_ids_are_equal() -> None:
    """Two MessageIds with the same UUID value are equal and have the same hash."""
    raw = "550e8400-e29b-41d4-a716-446655440000"
    first = MessageId.from_string(raw)
    second = MessageId.from_string(raw)

    assert first == second
    assert hash(first) == hash(second)


def test_different_message_ids_are_not_equal() -> None:
    """Two MessageIds with different UUID values are not equal."""
    first = MessageId()
    second = MessageId()

    assert first != second
