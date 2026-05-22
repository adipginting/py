"""Dispatcher tool executor."""

from py_coding_agent.domain.tool_call import ToolCall
from py_coding_agent.ports.tool_executor import ToolExecutionResult, ToolExecutor


class DispatcherToolExecutor(ToolExecutor):
    """Dispatches tool calls to the appropriate executor based on tool name."""

    def __init__(self, executors: dict[str, ToolExecutor]) -> None:
        self._executors = executors

    async def execute(self, tool_call: ToolCall) -> ToolExecutionResult:
        """Execute a tool call by dispatching to the appropriate executor."""
        executor = self._executors.get(tool_call.name)
        if executor is None:
            return ToolExecutionResult(content=f"Unknown tool: {tool_call.name}", is_error=True)
        return await executor.execute(tool_call)
