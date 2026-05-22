"""JsonFileSessionStore adapter: persist sessions as JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from py_coding_agent.domain.agent_state import AgentState
from py_coding_agent.domain.message import (
    AssistantMessage,
    Message,
    ToolResultMessage,
    UserMessage,
)
from py_coding_agent.domain.message_id import MessageId
from py_coding_agent.domain.session import Session
from py_coding_agent.domain.session_id import SessionId
from py_coding_agent.domain.tool_call import ToolCall
from py_coding_agent.domain.tool_call_id import ToolCallId


def _message_to_dict(msg: Message) -> dict[str, Any]:
    """Serialize a domain Message to a JSON-serializable dict."""
    if isinstance(msg, UserMessage):
        return {
            "type": "user",
            "id": str(msg.id.value),
            "text": msg.text,
        }
    if isinstance(msg, AssistantMessage):
        return {
            "type": "assistant",
            "id": str(msg.id.value),
            "text": msg.text,
            "tool_calls": [
                {
                    "id": str(tc.id.value),
                    "name": tc.name,
                    "arguments": tc.arguments,
                }
                for tc in msg.tool_calls
            ],
        }
    if isinstance(msg, ToolResultMessage):
        return {
            "type": "tool",
            "id": str(msg.id.value),
            "tool_call_id": str(msg.tool_call_id.value),
            "content": msg.content,
            "is_error": msg.is_error,
        }
    raise ValueError(f"Unknown message type: {type(msg)}")


def _message_from_dict(data: dict[str, Any]) -> Message:
    """Deserialize a dict back into a domain Message."""
    msg_type = data["type"]
    if msg_type == "user":
        return UserMessage(
            id=MessageId.from_string(data["id"]),
            text=data["text"],
        )
    if msg_type == "assistant":
        tool_calls = tuple(
            ToolCall(
                id=ToolCallId.from_string(tc["id"]),
                name=tc["name"],
                arguments=tc["arguments"],
            )
            for tc in data.get("tool_calls", [])
        )
        return AssistantMessage(
            id=MessageId.from_string(data["id"]),
            text=data.get("text", ""),
            tool_calls=tool_calls,
        )
    if msg_type == "tool":
        return ToolResultMessage(
            id=MessageId.from_string(data["id"]),
            tool_call_id=ToolCallId.from_string(data["tool_call_id"]),
            content=data["content"],
            is_error=data.get("is_error", False),
        )
    raise ValueError(f"Unknown message type: {msg_type}")


def _session_to_dict(session: Session) -> dict[str, Any]:
    """Serialize a Session to a JSON-serializable dict."""
    return {
        "id": session.id.value,
        "name": session.name,
        "messages": [_message_to_dict(m) for m in session.state.messages],
    }


def _session_from_dict(data: dict[str, Any]) -> Session:
    """Deserialize a dict back into a Session aggregate."""
    state = AgentState()
    for msg_data in data.get("messages", []):
        state.messages.append(_message_from_dict(msg_data))

    return Session(
        id=SessionId.from_string(data["id"]),
        name=data["name"],
        state=state,
    )


class JsonFileSessionStore:
    """Store sessions as JSON files on disk.

    Each session is written to ``<base_dir>/<session_id>.json``.
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        if base_dir is None:
            base_dir = Path.home() / ".py_coding_agent" / "sessions"
        self.base_dir = base_dir

    def _path(self, session_id: SessionId) -> Path:
        return self.base_dir / f"{session_id.value}.json"

    async def save(self, session: Session) -> None:
        """Persist a session to a JSON file."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        path = self._path(session.id)
        path.write_text(json.dumps(_session_to_dict(session), indent=2), encoding="utf-8")

    async def load(self, session_id: SessionId) -> Session | None:
        """Load a session from a JSON file."""
        path = self._path(session_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return _session_from_dict(data)

    async def list(self) -> list[SessionId]:
        """Return IDs of all stored sessions."""
        if not self.base_dir.exists():
            return []
        ids: list[SessionId] = []
        for path in self.base_dir.glob("*.json"):
            ids.append(SessionId.from_string(path.stem))
        return ids

    async def delete(self, session_id: SessionId) -> None:
        """Remove a session file."""
        path = self._path(session_id)
        if path.exists():
            path.unlink()
