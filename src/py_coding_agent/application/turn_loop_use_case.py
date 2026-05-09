"""TurnLoopUseCase: orchestrate a full turn including tool execution loops."""

from __future__ import annotations

from dataclasses import dataclass

from py_coding_agent.application.execute_tool_use_case import ExecuteToolUseCase
from py_coding_agent.application.prompt_use_case import PromptUseCase
from py_coding_agent.domain.agent_state import AgentState
from py_coding_agent.domain.events import DomainEvent
from py_coding_agent.domain.message import AssistantMessage
from py_coding_agent.domain.tool_definition import ToolDefinition
from py_coding_agent.ports.llm_provider import LLMProvider
from py_coding_agent.ports.tool_executor import ToolExecutor


@dataclass(frozen=True)
class TurnResult:
    """Result of executing a full turn."""

    assistant_messages: list[AssistantMessage]
    events: list[DomainEvent]


class TurnLoopUseCase:
    """Orchestrate the full agent turn loop.

    1. Prompt the LLM with the user's message.
    2. If the assistant requests tool calls, execute them and re-prompt.
    3. Repeat until the assistant's response contains no tool calls.
    """

    def __init__(
        self,
        *,
        llm_provider: LLMProvider,
        tool_executor: ToolExecutor,
    ) -> None:
        self._prompt = PromptUseCase(llm_provider=llm_provider)
        self._execute = ExecuteToolUseCase(tool_executor=tool_executor)

    async def execute(
        self,
        *,
        state: AgentState,
        text: str,
        model: str = "openai/gpt-4o",
        tools: list[ToolDefinition] | None = None,
        system_prompt: str = "",
    ) -> TurnResult:
        """Execute a full turn.

        Returns all assistant messages produced (one or more, if tool loops ran)
        and the aggregated domain events.
        """
        assistant_messages: list[AssistantMessage] = []
        events: list[DomainEvent] = []

        # Initial prompt
        result = await self._prompt.execute(
            state=state,
            text=text,
            model=model,
            tools=tools,
            system_prompt=system_prompt,
        )
        assistant_messages.append(result.assistant_message)
        events.extend(result.events)

        # Tool execution loop
        while result.assistant_message.tool_calls:
            for tool_call in result.assistant_message.tool_calls:
                exec_result = await self._execute.execute(
                    state=state,
                    tool_call_id=tool_call.id,
                )
                events.extend(exec_result.events)

            # Re-prompt with tool results in context
            result = await self._prompt.execute(
                state=state,
                text="",  # Empty: the pending tool results are context
                model=model,
                tools=tools,
                system_prompt=system_prompt,
            )
            assistant_messages.append(result.assistant_message)
            events.extend(result.events)

        return TurnResult(
            assistant_messages=assistant_messages,
            events=events,
        )
