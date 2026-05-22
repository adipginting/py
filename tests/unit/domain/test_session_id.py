"""Tests for SessionId value object."""

from py_coding_agent.domain.session_id import SessionId


def test_session_id_generates_string_by_default() -> None:
    """Creating a SessionId without arguments yields a non-empty string."""
    session_id = SessionId()

    assert isinstance(session_id.value, str)
    assert len(session_id.value) > 0


def test_session_id_can_be_created_from_string() -> None:
    """A SessionId can be constructed from an arbitrary string."""
    raw = "sess-abc-123"

    session_id = SessionId.from_string(raw)

    assert session_id.value == raw


def test_equal_session_ids_are_equal() -> None:
    """Two SessionIds with the same value are equal and have the same hash."""
    raw = "sess-xyz"
    first = SessionId.from_string(raw)
    second = SessionId.from_string(raw)

    assert first == second
    assert hash(first) == hash(second)


def test_different_session_ids_are_not_equal() -> None:
    """Two SessionIds with different values are not equal."""
    first = SessionId()
    second = SessionId()

    assert first != second
