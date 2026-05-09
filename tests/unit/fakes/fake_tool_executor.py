"""Fake ToolExecutor for testing."""

from __future__ import annotations

from py_coding_agent.domain.tool_call import ToolCall
from py_coding_agent.ports.tool_executor import ToolExecutionInvocation, ToolExecutionResult


class FakeToolExecutor:
    """A programmable fake tool executor for unit tests.

    Returns preset results for known tool names. Records every invocation.
    """

    def __init__(self, results: dict[str, ToolExecutionResult] | None = None) -> None:
        self.results = results or {}
        self.invocations: list[ToolExecutionInvocation] = []

    async def execute(self, tool_call: ToolCall) -> ToolExecutionResult:
        """Return the programmed result and record the invocation."""
        self.invocations.append(
            ToolExecutionInvocation(
                name=tool_call.name,
                arguments=tool_call.arguments,
            )
        )
        return self.results.get(
            tool_call.name,
            ToolExecutionResult(content=""),
        )
