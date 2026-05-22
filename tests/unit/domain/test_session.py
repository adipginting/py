"""Tests for Session aggregate."""

from py_coding_agent.domain.agent_state import AgentState
from py_coding_agent.domain.message import UserMessage
from py_coding_agent.domain.session import Session
from py_coding_agent.domain.session_id import SessionId


def test_session_has_id_and_name() -> None:
    """A session is created with an ID, name, and empty state."""
    session_id = SessionId.from_string("sess-1")
    session = Session(id=session_id, name="Test Session")

    assert session.id == session_id
    assert session.name == "Test Session"
    assert isinstance(session.state, AgentState)
    assert session.state.messages == []


def test_session_renames() -> None:
    """A session can be renamed."""
    session = Session(id=SessionId(), name="Old")

    session.rename("New")

    assert session.name == "New"


def test_session_tracks_turns_via_state() -> None:
    """Messages appended to the session state are part of the session."""
    session = Session(id=SessionId(), name="Turn Test")

    session.state.append_user_message(UserMessage(text="Hello"))

    assert len(session.state.messages) == 1
    first = session.state.messages[0]
    assert isinstance(first, UserMessage)
    assert first.text == "Hello"


def test_session_branch_copies_messages_up_to_index() -> None:
    """Branching at index N copies messages[0:N+1] into a new session."""
    session = Session(id=SessionId.from_string("orig"), name="Original")
    session.state.append_user_message(UserMessage(text="First"))
    session.state.append_user_message(UserMessage(text="Second"))
    session.state.append_user_message(UserMessage(text="Third"))

    branch = session.branch_at(1, name="Branch")

    assert branch.id != session.id
    assert branch.name == "Branch"
    assert len(branch.state.messages) == 2
    first = branch.state.messages[0]
    second = branch.state.messages[1]
    assert isinstance(first, UserMessage)
    assert isinstance(second, UserMessage)
    assert first.text == "First"
    assert second.text == "Second"


def test_session_branch_does_not_mutate_original() -> None:
    """Branching leaves the original session unchanged."""
    session = Session(id=SessionId.from_string("orig"), name="Original")
    session.state.append_user_message(UserMessage(text="First"))

    branch = session.branch_at(0, name="Branch")
    branch.state.append_user_message(UserMessage(text="Added to branch"))

    assert len(session.state.messages) == 1
    assert len(branch.state.messages) == 2


def test_session_branch_with_negative_index_counts_from_end() -> None:
    """A negative index counts from the end of the message list."""
    session = Session(id=SessionId.from_string("orig"), name="Original")
    session.state.append_user_message(UserMessage(text="First"))
    session.state.append_user_message(UserMessage(text="Second"))
    session.state.append_user_message(UserMessage(text="Third"))

    branch = session.branch_at(-1, name="Branch")

    assert len(branch.state.messages) == 3
    last = branch.state.messages[-1]
    assert isinstance(last, UserMessage)
    assert last.text == "Third"


def test_session_branch_at_latest_creates_full_copy() -> None:
    """Branching at the last index creates a complete copy."""
    session = Session(id=SessionId.from_string("orig"), name="Original")
    session.state.append_user_message(UserMessage(text="Only"))

    branch = session.branch_at(0, name="Copy")

    assert len(branch.state.messages) == 1
    only = branch.state.messages[0]
    assert isinstance(only, UserMessage)
    assert only.text == "Only"
