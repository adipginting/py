"""Tests for TurnLoopUseCase."""

import pytest

from py_coding_agent.application.turn_loop_use_case import TurnLoopUseCase
from py_coding_agent.domain.agent_state import AgentState
from py_coding_agent.domain.message import AssistantMessage, ToolResultMessage, UserMessage
from py_coding_agent.domain.tool_call import ToolCall
from py_coding_agent.domain.tool_call_id import ToolCallId
from py_coding_agent.domain.tool_definition import ToolDefinition
from py_coding_agent.ports.llm_provider import (
    StopEvent,
    TextChunk,
    ToolCallChunk,
)
from py_coding_agent.ports.tool_executor import ToolExecutionResult
from tests.unit.fakes.fake_llm_provider import FakeLLMProvider
from tests.unit.fakes.fake_tool_executor import FakeToolExecutor


@pytest.mark.anyio
async def test_turn_with_no_tool_calls_returns_single_assistant_message() -> None:
    """A simple prompt-response turn produces one assistant message and stops."""
    llm = FakeLLMProvider(events_per_call=[[TextChunk(text="Hello!"), StopEvent(reason="stop")]])
    executor = FakeToolExecutor()
    use_case = TurnLoopUseCase(llm_provider=llm, tool_executor=executor)
    state = AgentState()

    result = await use_case.execute(state=state, text="Hi")

    assert len(state.messages) == 2
    assert isinstance(state.messages[0], UserMessage)
    assert isinstance(state.messages[1], AssistantMessage)
    assert state.messages[1].text == "Hello!"
    assert state.messages[1].tool_calls == ()
    assert len(result.assistant_messages) == 1


@pytest.mark.anyio
async def test_turn_executes_tool_calls_and_reprompts() -> None:
    """When the assistant requests tools, they execute and the LLM is called again."""
    tool_call_id = ToolCallId.from_string("550e8400-e29b-41d4-a716-446655440000")
    tool_call = ToolCall(id=tool_call_id, name="read", arguments={"path": "/etc/hosts"})

    llm = FakeLLMProvider(
        events_per_call=[
            [ToolCallChunk(tool_call=tool_call), StopEvent(reason="tool_calls")],
            [TextChunk(text="Done!"), StopEvent(reason="stop")],
        ]
    )
    executor = FakeToolExecutor(
        results={"read": ToolExecutionResult(content="127.0.0.1 localhost")}
    )
    use_case = TurnLoopUseCase(llm_provider=llm, tool_executor=executor)
    state = AgentState()

    result = await use_case.execute(state=state, text="Read /etc/hosts")

    assert len(state.messages) == 4
    assert isinstance(state.messages[1], AssistantMessage)
    assert isinstance(state.messages[2], ToolResultMessage)
    assert state.messages[2].content == "127.0.0.1 localhost"
    assert isinstance(state.messages[3], AssistantMessage)
    assert state.messages[3].text == "Done!"
    assert len(llm.invocations) == 2
    assert len(result.assistant_messages) == 2


@pytest.mark.anyio
async def test_turn_executes_multiple_tools_in_one_call() -> None:
    """Multiple tool calls from one assistant message are all executed before reprompt."""
    tc1 = ToolCall(
        id=ToolCallId.from_string("550e8400-e29b-41d4-a716-446655440000"),
        name="read",
        arguments={"path": "a"},
    )
    tc2 = ToolCall(
        id=ToolCallId.from_string("550e8400-e29b-41d4-a716-446655440001"),
        name="read",
        arguments={"path": "b"},
    )

    llm = FakeLLMProvider(
        events_per_call=[
            [
                ToolCallChunk(tool_call=tc1),
                ToolCallChunk(tool_call=tc2),
                StopEvent(reason="tool_calls"),
            ],
            [TextChunk(text="Both done"), StopEvent(reason="stop")],
        ]
    )
    executor = FakeToolExecutor(results={"read": ToolExecutionResult(content="content")})
    use_case = TurnLoopUseCase(llm_provider=llm, tool_executor=executor)
    state = AgentState()

    await use_case.execute(state=state, text="Read a and b")

    assert len(executor.invocations) == 2
    assert len(state.messages) == 5
    assert state.messages[3].content == "content"


@pytest.mark.anyio
async def test_turn_forwards_tools_to_provider() -> None:
    """Available tool definitions are forwarded to every provider call."""
    llm = FakeLLMProvider(events_per_call=[[TextChunk(text="OK"), StopEvent(reason="stop")]])
    executor = FakeToolExecutor()
    use_case = TurnLoopUseCase(llm_provider=llm, tool_executor=executor)
    state = AgentState()
    tool_def = ToolDefinition(name="read", description="Read file", parameters={})

    await use_case.execute(state=state, text="Hi", tools=[tool_def])

    assert len(llm.invocations) == 1
    assert llm.invocations[0].tools == [tool_def]
