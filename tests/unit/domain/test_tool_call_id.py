"""Tests for ToolCallId value object."""

from py_coding_agent.domain.tool_call_id import ToolCallId


def test_tool_call_id_generates_string_by_default() -> None:
    """Creating a ToolCallId without arguments yields a string."""
    tool_call_id = ToolCallId()

    assert isinstance(tool_call_id.value, str)
    assert len(tool_call_id.value) > 0


def test_tool_call_id_can_be_created_from_string() -> None:
    """A ToolCallId can be constructed from an arbitrary string."""
    raw = "call_abc123"

    tool_call_id = ToolCallId.from_string(raw)

    assert tool_call_id.value == raw


def test_equal_tool_call_ids_are_equal() -> None:
    """Two ToolCallIds with the same value are equal and have the same hash."""
    raw = "call_xyz"
    first = ToolCallId.from_string(raw)
    second = ToolCallId.from_string(raw)

    assert first == second
    assert hash(first) == hash(second)


def test_different_tool_call_ids_are_not_equal() -> None:
    """Two ToolCallIds with different values are not equal."""
    first = ToolCallId()
    second = ToolCallId()

    assert first != second
