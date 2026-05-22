"""Tests for InMemorySessionStore adapter."""

from __future__ import annotations

import pytest

from py_coding_agent.adapters.in_memory_session_store import InMemorySessionStore
from py_coding_agent.domain.session import Session
from py_coding_agent.domain.session_id import SessionId


@pytest.mark.anyio
async def test_in_memory_store_saves_and_loads() -> None:
    """A saved session can be loaded back by its ID."""
    store = InMemorySessionStore()
    session = Session(id=SessionId.from_string("sess-1"), name="Test")

    await store.save(session)
    loaded = await store.load(session.id)

    assert loaded is not None
    assert loaded.id == session.id
    assert loaded.name == "Test"
    # Should be the same object reference for in-memory store
    assert loaded is session


@pytest.mark.anyio
async def test_in_memory_store_returns_none_for_missing_session() -> None:
    """Loading an unknown session ID returns None."""
    store = InMemorySessionStore()

    loaded = await store.load(SessionId.from_string("missing"))

    assert loaded is None


@pytest.mark.anyio
async def test_in_memory_store_lists_sessions() -> None:
    """List returns IDs of all saved sessions."""
    store = InMemorySessionStore()
    session_a = Session(id=SessionId.from_string("a"), name="A")
    session_b = Session(id=SessionId.from_string("b"), name="B")

    await store.save(session_a)
    await store.save(session_b)
    ids = await store.list()

    assert len(ids) == 2
    assert SessionId.from_string("a") in ids
    assert SessionId.from_string("b") in ids


@pytest.mark.anyio
async def test_in_memory_store_deletes_session() -> None:
    """Deleting a session removes it from the store."""
    store = InMemorySessionStore()
    session = Session(id=SessionId.from_string("sess-1"), name="Test")

    await store.save(session)
    await store.delete(session.id)
    loaded = await store.load(session.id)

    assert loaded is None
    assert await store.list() == []


@pytest.mark.anyio
async def test_in_memory_store_overwrites_on_save() -> None:
    """Saving a session with an existing ID replaces the old one."""
    store = InMemorySessionStore()
    session = Session(id=SessionId.from_string("sess-1"), name="Old")

    await store.save(session)
    session.rename("New")
    await store.save(session)
    loaded = await store.load(session.id)

    assert loaded is not None
    assert loaded.name == "New"
