"""Tests for ToolExecutor port and FakeToolExecutor."""

import pytest

from py_coding_agent.domain.tool_call import ToolCall
from py_coding_agent.domain.tool_call_id import ToolCallId
from py_coding_agent.ports.tool_executor import ToolExecutionResult, ToolExecutor
from tests.unit.fakes.fake_tool_executor import FakeToolExecutor


def test_tool_executor_is_implementable() -> None:
    """FakeToolExecutor must satisfy the ToolExecutor protocol."""
    fake: ToolExecutor = FakeToolExecutor()
    assert fake is not None


@pytest.mark.anyio
async def test_fake_executes_registered_tool() -> None:
    """FakeToolExecutor returns the programmed result for a known tool."""
    fake = FakeToolExecutor(results={"read": ToolExecutionResult(content="file contents")})
    tool_call = ToolCall(
        id=ToolCallId.from_string("550e8400-e29b-41d4-a716-446655440000"),
        name="read",
        arguments={"path": "/etc/hosts"},
    )

    result = await fake.execute(tool_call)

    assert result.content == "file contents"
    assert result.is_error is False


@pytest.mark.anyio
async def test_fake_executes_registered_tool_with_error() -> None:
    """FakeToolExecutor can return error results."""
    fake = FakeToolExecutor(
        results={"read": ToolExecutionResult(content="not found", is_error=True)}
    )
    tool_call = ToolCall(
        id=ToolCallId(),
        name="read",
        arguments={"path": "/nonexistent"},
    )

    result = await fake.execute(tool_call)

    assert result.is_error is True
    assert result.content == "not found"


@pytest.mark.anyio
async def test_fake_records_invocations() -> None:
    """FakeToolExecutor records every execution for later verification."""
    fake = FakeToolExecutor(results={"bash": ToolExecutionResult(content="output")})
    tool_call = ToolCall(id=ToolCallId(), name="bash", arguments={"command": "echo hi"})

    await fake.execute(tool_call)

    assert len(fake.invocations) == 1
    assert fake.invocations[0].name == "bash"
    assert fake.invocations[0].arguments == {"command": "echo hi"}
