"""InMemorySessionStore adapter: volatile in-memory session storage."""

from __future__ import annotations

from py_coding_agent.domain.session import Session
from py_coding_agent.domain.session_id import SessionId


class InMemorySessionStore:
    """Store sessions in memory.

    All data is lost when the process exits.
    Useful for testing and ephemeral sessions.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    async def save(self, session: Session) -> None:
        """Persist a session in memory."""
        self._sessions[session.id.value] = session

    async def load(self, session_id: SessionId) -> Session | None:
        """Load a session by ID."""
        return self._sessions.get(session_id.value)

    async def list(self) -> list[SessionId]:
        """Return IDs of all stored sessions."""
        return [s.id for s in self._sessions.values()]

    async def delete(self, session_id: SessionId) -> None:
        """Remove a session from memory."""
        self._sessions.pop(session_id.value, None)
