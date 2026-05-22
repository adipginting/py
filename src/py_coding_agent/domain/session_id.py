"""SessionId value object."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class SessionId:
    """Unique identifier for a session.

    Immutable value object. Two SessionIds are equal if and only if
    their underlying string values are equal.
    """

    value: str

    def __init__(self, value: str | None = None) -> None:
        object.__setattr__(self, "value", value if value is not None else str(uuid4()))

    @classmethod
    def from_string(cls, raw: str) -> SessionId:
        """Create a SessionId from a raw string."""
        return cls(raw)
