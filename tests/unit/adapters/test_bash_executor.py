"""Tests for BashExecutor adapter."""

import pytest

from py_coding_agent.adapters.bash_executor import BashExecutor
from py_coding_agent.domain.tool_call import ToolCall
from py_coding_agent.domain.tool_call_id import ToolCallId


@pytest.mark.anyio
async def test_bash_executor_runs_command() -> None:
    """BashExecutor runs a simple command and returns stdout."""
    executor = BashExecutor()
    tool_call = ToolCall(
        id=ToolCallId(),
        name="bash",
        arguments={"command": "echo hello"},
    )

    result = await executor.execute(tool_call)

    assert result.content == "hello"
    assert result.is_error is False


@pytest.mark.anyio
async def test_bash_executor_returns_stderr_on_failure() -> None:
    """A failing command returns stderr with is_error=True."""
    executor = BashExecutor()
    tool_call = ToolCall(
        id=ToolCallId(),
        name="bash",
        arguments={"command": "cat /nonexistent_file_12345"},
    )

    result = await executor.execute(tool_call)

    assert result.is_error is True
    assert "No such file" in result.content or "cannot open" in result.content.lower()
