"""Tests for JsonFileSessionStore adapter."""

from __future__ import annotations

from pathlib import Path

import pytest

from py_coding_agent.adapters.json_file_session_store import JsonFileSessionStore
from py_coding_agent.domain.message import UserMessage
from py_coding_agent.domain.session import Session
from py_coding_agent.domain.session_id import SessionId


@pytest.fixture
def tmp_store(tmp_path: Path) -> JsonFileSessionStore:
    """Provide a JsonFileSessionStore backed by a temporary directory."""
    return JsonFileSessionStore(base_dir=tmp_path)


@pytest.mark.anyio
async def test_json_file_store_saves_and_loads(tmp_store: JsonFileSessionStore) -> None:
    """A saved session can be loaded back by its ID."""
    session = Session(id=SessionId.from_string("sess-1"), name="Test")
    session.state.append_user_message(UserMessage(text="Hello"))

    await tmp_store.save(session)
    loaded = await tmp_store.load(session.id)

    assert loaded is not None
    assert loaded.id == session.id
    assert loaded.name == "Test"
    assert len(loaded.state.messages) == 1
    msg = loaded.state.messages[0]
    assert isinstance(msg, UserMessage)
    assert msg.text == "Hello"


@pytest.mark.anyio
async def test_json_file_store_returns_none_for_missing_session(
    tmp_store: JsonFileSessionStore,
) -> None:
    """Loading an unknown session ID returns None."""
    loaded = await tmp_store.load(SessionId.from_string("missing"))

    assert loaded is None


@pytest.mark.anyio
async def test_json_file_store_lists_sessions(tmp_store: JsonFileSessionStore) -> None:
    """List returns IDs of all saved sessions."""
    session_a = Session(id=SessionId.from_string("a"), name="A")
    session_b = Session(id=SessionId.from_string("b"), name="B")

    await tmp_store.save(session_a)
    await tmp_store.save(session_b)
    ids = await tmp_store.list()

    assert len(ids) == 2
    assert SessionId.from_string("a") in ids
    assert SessionId.from_string("b") in ids


@pytest.mark.anyio
async def test_json_file_store_deletes_session(tmp_store: JsonFileSessionStore) -> None:
    """Deleting a session removes it from the store."""
    session = Session(id=SessionId.from_string("sess-1"), name="Test")

    await tmp_store.save(session)
    await tmp_store.delete(session.id)
    loaded = await tmp_store.load(session.id)

    assert loaded is None
    assert await tmp_store.list() == []


@pytest.mark.anyio
async def test_json_file_store_overwrites_on_save(tmp_store: JsonFileSessionStore) -> None:
    """Saving a session with an existing ID replaces the old file."""
    session = Session(id=SessionId.from_string("sess-1"), name="Old")

    await tmp_store.save(session)
    session.rename("New")
    await tmp_store.save(session)
    loaded = await tmp_store.load(session.id)

    assert loaded is not None
    assert loaded.name == "New"


@pytest.mark.anyio
async def test_json_file_store_creates_directory_if_missing(tmp_path: Path) -> None:
    """The store creates the base directory if it does not exist."""
    nested = tmp_path / "nested" / "sessions"
    store = JsonFileSessionStore(base_dir=nested)
    session = Session(id=SessionId.from_string("sess-1"), name="Test")

    await store.save(session)

    assert nested.exists()
    assert (nested / "sess-1.json").exists()


def test_json_file_store_default_base_dir() -> None:
    """Default base_dir resolves to ~/.py_coding_agent/sessions."""
    store = JsonFileSessionStore()
    assert "py_coding_agent" in str(store.base_dir)
    assert "sessions" in str(store.base_dir)
