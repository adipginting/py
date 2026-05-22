"""SessionStore port: persist and retrieve conversation sessions."""

from __future__ import annotations

from typing import Protocol

from py_coding_agent.domain.session import Session
from py_coding_agent.domain.session_id import SessionId


class SessionStore(Protocol):
    """Outbound port for session persistence.

    Implementations may store sessions in memory, JSON files,
    databases, or remote services.
    """

    async def save(self, session: Session) -> None:
        """Persist a session. Overwrites any existing session with the same ID."""
        ...

    async def load(self, session_id: SessionId) -> Session | None:
        """Load a session by ID.

        Returns None if the session does not exist.
        """
        ...

    async def list(self) -> list[SessionId]:
        """Return IDs of all persisted sessions."""
        ...

    async def delete(self, session_id: SessionId) -> None:
        """Remove a session from the store.

        No-op if the session does not exist.
        """
        ...
