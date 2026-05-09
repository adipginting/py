"""ToolExecutor port: the outbound interface for executing tool calls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from py_coding_agent.domain.tool_call import ToolCall


@dataclass(frozen=True)
class ToolExecutionResult:
    """The output of a tool execution."""

    content: str
    is_error: bool = False


@dataclass(frozen=True)
class ToolExecutionInvocation:
    """A record of a tool execution for testing."""

    name: str
    arguments: dict[str, object]


class ToolExecutor(Protocol):
    """Outbound port for executing tool calls.

    Implementations handle the specifics of each tool (bash, read, edit, etc.).
    """

    async def execute(self, tool_call: ToolCall) -> ToolExecutionResult:
        """Execute a tool call and return the result."""
        ...
