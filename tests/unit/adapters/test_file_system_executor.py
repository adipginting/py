"""Tests for FileSystemExecutor adapter."""

import pytest

from py_coding_agent.adapters.file_system_executor import FileSystemExecutor
from py_coding_agent.domain.tool_call import ToolCall
from py_coding_agent.domain.tool_call_id import ToolCallId


@pytest.mark.anyio
async def test_file_system_executor_reads_file(tmp_path) -> None:
    """The read tool reads a file and returns its contents."""
    path = tmp_path / "test.txt"
    path.write_text("hello world")
    executor = FileSystemExecutor(cwd=str(tmp_path))
    tool_call = ToolCall(
        id=ToolCallId(),
        name="read",
        arguments={"path": str(tmp_path / "test.txt")},
    )

    result = await executor.execute(tool_call)

    assert result.content == "hello world"
    assert result.is_error is False


@pytest.mark.anyio
async def test_file_system_executor_writes_file(tmp_path) -> None:
    """The write tool creates a file with given contents."""
    executor = FileSystemExecutor(cwd=str(tmp_path))
    tool_call = ToolCall(
        id=ToolCallId(),
        name="write",
        arguments={
            "path": str(tmp_path / "output.txt"),
            "content": "new content",
        },
    )

    result = await executor.execute(tool_call)

    assert result.is_error is False
    assert (tmp_path / "output.txt").read_text() == "new content"


@pytest.mark.anyio
async def test_file_system_executor_returns_error_for_missing_file(tmp_path) -> None:
    """Reading a nonexistent file returns an error."""
    executor = FileSystemExecutor(cwd=str(tmp_path))
    tool_call = ToolCall(
        id=ToolCallId(),
        name="read",
        arguments={"path": str(tmp_path / "nonexistent.txt")},
    )

    result = await executor.execute(tool_call)

    assert result.is_error is True
    assert "No such file" in result.content or "not found" in result.content.lower()
