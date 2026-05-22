"""Session aggregate root."""

from __future__ import annotations

from dataclasses import dataclass, field

from py_coding_agent.domain.agent_state import AgentState
from py_coding_agent.domain.session_id import SessionId


@dataclass
class Session:
    """The aggregate root for a persisted conversation.

    A session is an ordered sequence of turns backed by an AgentState.
    It supports naming and will later support branching and compaction.
    """

    id: SessionId
    name: str = "Untitled"
    state: AgentState = field(default_factory=AgentState)

    def rename(self, name: str) -> None:
        """Rename the session."""
        self.name = name

    def branch_at(self, index: int, *, name: str = "Branch") -> Session:
        """Fork a new session at the given message index.

        The new session contains all messages up to and including *index*.
        Negative indices count from the end of the message list.

        Args:
            index: The last message to include in the branch.
            name: The name for the new session.

        Returns:
            A new Session with a fresh ID and copied messages.
        """
        normalized = index if index >= 0 else len(self.state.messages) + index
        copied_messages = list(self.state.messages[: normalized + 1])
        branch_state = AgentState()
        branch_state.messages.extend(copied_messages)
        return Session(
            id=SessionId(),
            name=name,
            state=branch_state,
        )
