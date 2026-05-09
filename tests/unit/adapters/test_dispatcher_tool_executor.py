"""Tests for DispatcherToolExecutor."""

from __future__ import annotations

import pytest

from py_coding_agent.adapters.dispatcher_tool_executor import DispatcherToolExecutor
from py_coding_agent.adapters.file_system_executor import FileSystemExecutor
from py_coding_agent.domain.tool_call import ToolCall
from py_coding_agent.domain.tool_call_id import ToolCallId


class FakeToolExecutor:
    """Fake for testing dispatch — records calls and returns fixed results."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[ToolCall] = []
        self._result = "done"

    async def execute(self, tool_call: ToolCall) -> object:
        self.calls.append(tool_call)
        return type("Result", (), {"content": self._result, "is_error": False})()


@pytest.mark.anyio
async def test_dispatcher_routes_by_tool_name() -> None:
    """Tool calls are routed to the executor matching the tool name."""
    bash = FakeToolExecutor("bash")
    read = FileSystemExecutor(cwd=".")
    dispatcher = DispatcherToolExecutor(
        executors={
            "bash": bash,
            "read": read,
        }
    )

    bash_call = ToolCall(id=ToolCallId(), name="bash", arguments={"command": "echo hi"})
    result = await dispatcher.execute(bash_call)

    assert len(bash.calls) == 1
    assert bash.calls[0].name == "bash"
    assert result.content == "done"


@pytest.mark.anyio
async def test_dispatcher_returns_error_for_unknown_tool() -> None:
    """An unregistered tool name returns an error result."""
    dispatcher = DispatcherToolExecutor(executors={})

    unknown = ToolCall(id=ToolCallId(), name="unknown", arguments={})
    result = await dispatcher.execute(unknown)

    assert result.is_error is True
    assert "unknown" in result.content
