"""CLI entrypoint for py-coding-agent."""

from __future__ import annotations

import asyncio

import click

from py_coding_agent.adapters.bash_executor import BashExecutor
from py_coding_agent.adapters.echo_provider import EchoProvider
from py_coding_agent.application.turn_loop_use_case import TurnLoopUseCase
from py_coding_agent.domain.agent_state import AgentState
from py_coding_agent.domain.tool_definition import ToolDefinition


@click.group()
def app() -> None:
    """py-coding-agent: A Python coding agent."""


@app.command("print")
@click.argument("prompt")
def print_command(prompt: str) -> None:
    """Run a single prompt and print the assistant response."""
    asyncio.run(_run_print(prompt))


async def _run_print(prompt: str) -> None:
    """Wiring: EchoProvider + BashExecutor + TurnLoopUseCase."""
    state = AgentState()
    llm = EchoProvider()
    executor = BashExecutor()
    use_case = TurnLoopUseCase(llm_provider=llm, tool_executor=executor)

    tool_def = ToolDefinition(
        name="bash",
        description="Execute a bash command",
        parameters={"command": {"type": "string"}},
    )

    result = await use_case.execute(
        state=state,
        text=prompt,
        tools=[tool_def],
    )

    for msg in result.assistant_messages:
        click.echo(msg.text)
