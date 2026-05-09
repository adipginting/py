"""ToolCall value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from py_coding_agent.domain.tool_call_id import ToolCallId


@dataclass(frozen=True)
class ToolCall:
    """A request by the assistant to invoke a named tool."""

    id: ToolCallId
    name: str
    arguments: dict[str, Any]
