"""Tests for ToolCallId value object."""

from uuid import UUID

from py_coding_agent.domain.tool_call_id import ToolCallId


def test_tool_call_id_generates_valid_uuid_by_default() -> None:
    """Creating a ToolCallId without arguments yields a valid UUID."""
    tool_call_id = ToolCallId()

    assert isinstance(tool_call_id.value, UUID)


def test_tool_call_id_can_be_created_from_uuid_string() -> None:
    """A ToolCallId can be constructed from a UUID string."""
    raw = "550e8400-e29b-41d4-a716-446655440000"

    tool_call_id = ToolCallId.from_string(raw)

    assert str(tool_call_id.value) == raw


def test_equal_tool_call_ids_are_equal() -> None:
    """Two ToolCallIds with the same UUID value are equal and have the same hash."""
    raw = "550e8400-e29b-41d4-a716-446655440000"
    first = ToolCallId.from_string(raw)
    second = ToolCallId.from_string(raw)

    assert first == second
    assert hash(first) == hash(second)


def test_different_tool_call_ids_are_not_equal() -> None:
    """Two ToolCallIds with different UUID values are not equal."""
    first = ToolCallId()
    second = ToolCallId()

    assert first != second
