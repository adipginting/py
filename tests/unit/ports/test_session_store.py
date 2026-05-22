"""Tests for SessionStore port."""

from __future__ import annotations

import pytest

from py_coding_agent.domain.session import Session
from py_coding_agent.domain.session_id import SessionId


class FakeSessionStore:
    """Hand-written fake for SessionStore."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self.calls: list[str] = []

    async def save(self, session: Session) -> None:
        self.calls.append(f"save:{session.id.value}")
        self._sessions[session.id.value] = session

    async def load(self, session_id: SessionId) -> Session | None:
        self.calls.append(f"load:{session_id.value}")
        return self._sessions.get(session_id.value)

    async def list(self) -> list[SessionId]:
        self.calls.append("list")
        return [s.id for s in self._sessions.values()]

    async def delete(self, session_id: SessionId) -> None:
        self.calls.append(f"delete:{session_id.value}")
        self._sessions.pop(session_id.value, None)


@pytest.mark.anyio
async def test_session_store_saves_and_loads() -> None:
    """A saved session can be loaded back by its ID."""
    store = FakeSessionStore()
    session = Session(id=SessionId.from_string("sess-1"), name="Test")

    await store.save(session)
    loaded = await store.load(session.id)

    assert loaded is not None
    assert loaded.id == session.id
    assert loaded.name == "Test"


@pytest.mark.anyio
async def test_session_store_returns_none_for_missing_session() -> None:
    """Loading an unknown session ID returns None."""
    store = FakeSessionStore()

    loaded = await store.load(SessionId.from_string("missing"))

    assert loaded is None


@pytest.mark.anyio
async def test_session_store_lists_sessions() -> None:
    """List returns IDs of all saved sessions."""
    store = FakeSessionStore()
    session_a = Session(id=SessionId.from_string("a"), name="A")
    session_b = Session(id=SessionId.from_string("b"), name="B")

    await store.save(session_a)
    await store.save(session_b)
    ids = await store.list()

    assert len(ids) == 2


@pytest.mark.anyio
async def test_session_store_deletes_session() -> None:
    """Deleting a session removes it from the store."""
    store = FakeSessionStore()
    session = Session(id=SessionId.from_string("sess-1"), name="Test")

    await store.save(session)
    await store.delete(session.id)
    loaded = await store.load(session.id)

    assert loaded is None
