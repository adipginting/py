"""Tests for PromptUseCase."""

import pytest

from py_coding_agent.application.prompt_use_case import PromptUseCase
from py_coding_agent.domain.agent_state import AgentState
from py_coding_agent.domain.message import AssistantMessage, UserMessage
from py_coding_agent.domain.tool_call import ToolCall
from py_coding_agent.domain.tool_call_id import ToolCallId
from py_coding_agent.domain.tool_definition import ToolDefinition
from py_coding_agent.ports.llm_provider import StopEvent, TextChunk, ToolCallChunk, UsageEvent
from tests.unit.fakes.fake_llm_provider import FakeLLMProvider


@pytest.mark.anyio
async def test_prompt_use_case_appends_user_message() -> None:
    """When prompted, the user message is appended to the state."""
    fake = FakeLLMProvider(events=[TextChunk(text="Hi"), StopEvent(reason="stop")])
    use_case = PromptUseCase(llm_provider=fake)
    state = AgentState()

    await use_case.execute(state=state, text="Hello")

    assert len(state.messages) == 2
    assert isinstance(state.messages[0], UserMessage)
    assert state.messages[0].text == "Hello"


@pytest.mark.anyio
async def test_prompt_use_case_collects_assistant_response() -> None:
    """Text chunks from the LLM are collected into an AssistantMessage."""
    fake = FakeLLMProvider(
        events=[
            TextChunk(text="Hello, "),
            TextChunk(text="user!"),
            StopEvent(reason="stop"),
        ]
    )
    use_case = PromptUseCase(llm_provider=fake)
    state = AgentState()

    result = await use_case.execute(state=state, text="Hello")

    assert isinstance(state.messages[1], AssistantMessage)
    assert state.messages[1].text == "Hello, user!"
    assert state.messages[1].tool_calls == ()
    assert result.assistant_message.text == "Hello, user!"


@pytest.mark.anyio
async def test_prompt_use_case_collects_tool_calls() -> None:
    """Tool call chunks from the LLM are collected into the AssistantMessage."""
    tool_call_id = ToolCallId.from_string("550e8400-e29b-41d4-a716-446655440000")
    tool_call = ToolCall(id=tool_call_id, name="read", arguments={"path": "/etc/hosts"})
    fake = FakeLLMProvider(
        events=[
            TextChunk(text="I'll read that."),
            ToolCallChunk(tool_call=tool_call),
            StopEvent(reason="tool_calls"),
        ]
    )
    use_case = PromptUseCase(llm_provider=fake)
    state = AgentState()

    result = await use_case.execute(state=state, text="Read /etc/hosts")

    assert len(result.assistant_message.tool_calls) == 1
    assert result.assistant_message.tool_calls[0].name == "read"
    assert state.pending_tool_call_ids == {tool_call_id}


@pytest.mark.anyio
async def test_prompt_use_case_passes_tools_to_provider() -> None:
    """Available tools are forwarded to the LLM provider."""
    fake = FakeLLMProvider(events=[TextChunk(text="OK"), StopEvent(reason="stop")])
    use_case = PromptUseCase(llm_provider=fake)
    state = AgentState()
    tool_def = ToolDefinition(name="read", description="Read a file", parameters={})

    await use_case.execute(state=state, text="Hello", tools=[tool_def])

    assert len(fake.invocations) == 1
    assert fake.invocations[0].tools == [tool_def]


@pytest.mark.anyio
async def test_prompt_use_case_returns_events() -> None:
    """The use case returns the domain events produced by state changes."""
    fake = FakeLLMProvider(events=[TextChunk(text="Done"), StopEvent(reason="stop")])
    use_case = PromptUseCase(llm_provider=fake)
    state = AgentState()

    result = await use_case.execute(state=state, text="Hi")

    event_types = [type(e).__name__ for e in result.events]
    assert "MessageAppended" in event_types


@pytest.mark.anyio
async def test_prompt_use_case_records_token_usage() -> None:
    """UsageEvent from the stream is accumulated into AgentState."""
    fake = FakeLLMProvider(
        events=[
            TextChunk(text="Hi"),
            UsageEvent(input_tokens=10, output_tokens=2),
            StopEvent(reason="stop"),
        ]
    )
    use_case = PromptUseCase(llm_provider=fake)
    state = AgentState()

    result = await use_case.execute(state=state, text="Hello")

    assert state.token_usage.input_tokens == 10
    assert state.token_usage.output_tokens == 2
    assert state.token_usage.total_tokens == 12
    event_types = [type(e).__name__ for e in result.events]
    assert "TokenUsageRecorded" in event_types


@pytest.mark.anyio
async def test_prompt_use_case_sums_multiple_usage_events() -> None:
    """Multiple UsageEvent chunks are summed into a single TokenUsage."""
    fake = FakeLLMProvider(
        events=[
            TextChunk(text="Hello"),
            UsageEvent(input_tokens=5, output_tokens=1),
            UsageEvent(input_tokens=3, output_tokens=1),
            StopEvent(reason="stop"),
        ]
    )
    use_case = PromptUseCase(llm_provider=fake)
    state = AgentState()

    await use_case.execute(state=state, text="Hello")

    assert state.token_usage.input_tokens == 8
    assert state.token_usage.output_tokens == 2
