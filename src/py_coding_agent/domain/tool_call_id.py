"""ToolCallId value object."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class ToolCallId:
    """Unique identifier for a tool call.

    Immutable value object. Two ToolCallIds are equal if and only if
    their underlying UUID values are equal.
    """

    value: UUID

    def __init__(self, value: UUID | None = None) -> None:
        object.__setattr__(self, "value", value if value is not None else uuid4())

    @classmethod
    def from_string(cls, raw: str) -> ToolCallId:
        """Create a ToolCallId from a UUID string."""
        return cls(UUID(raw))
