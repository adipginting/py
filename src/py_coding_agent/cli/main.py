"""CLI entrypoint for py-coding-agent."""

from __future__ import annotations

import asyncio
import os

import click
import httpx

from py_coding_agent.adapters.anthropic_provider import AnthropicProvider
from py_coding_agent.adapters.bash_executor import BashExecutor
from py_coding_agent.adapters.echo_provider import EchoProvider
from py_coding_agent.adapters.file_system_executor import FileSystemExecutor
from py_coding_agent.adapters.openai_provider import OpenAIProvider
from py_coding_agent.adapters.retrying_llm_provider import RetryingLLMProvider
from py_coding_agent.application.turn_loop_use_case import TurnLoopUseCase
from py_coding_agent.domain.agent_state import AgentState
from py_coding_agent.domain.tool_definition import ToolDefinition
from py_coding_agent.ports.llm_provider import LLMProvider


@click.group()
def app() -> None:
    """py-coding-agent: A Python coding agent."""


def main() -> None:
    """Entry point for the CLI."""
    app()


def _create_provider(provider_name: str | None = None) -> LLMProvider:
    """Create an LLM provider based on environment or explicit choice.

    Priority:
      1. Explicit provider_name if given.
      2. OPENAI_API_KEY env var -> OpenAI.
      3. ANTHROPIC_API_KEY env var -> Anthropic.
      4. Fallback -> EchoProvider.
    """
    if provider_name == "openai" or (provider_name is None and os.environ.get("OPENAI_API_KEY")):
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise click.UsageError("OPENAI_API_KEY environment variable is required for openai provider.")
        openai_inner = OpenAIProvider(api_key=api_key, http_client=httpx.AsyncClient())
        return RetryingLLMProvider(openai_inner, max_retries=3, base_delay=1.0)

    if provider_name == "anthropic" or (provider_name is None and os.environ.get("ANTHROPIC_API_KEY")):
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise click.UsageError("ANTHROPIC_API_KEY environment variable is required for anthropic provider.")
        anthropic_inner = AnthropicProvider(api_key=api_key, http_client=httpx.AsyncClient())
        return RetryingLLMProvider(anthropic_inner, max_retries=3, base_delay=1.0)

    return EchoProvider()


def _create_tool_executor() -> BashExecutor | FileSystemExecutor:
    """Create the default tool executor."""
    return BashExecutor()


@app.command("print")
@click.argument("prompt")
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "echo"], case_sensitive=False),
    default=None,
    help="Override the LLM provider.",
)
@click.option(
    "--model",
    default=None,
    help="Override the model ID (provider-qualified, e.g. openai/gpt-4o).",
)
def print_command(prompt: str, provider: str | None, model: str | None) -> None:
    """Run a single prompt and print the assistant response."""
    asyncio.run(_run_print(prompt, provider_name=provider, model_override=model))


async def _run_print(
    prompt: str,
    *,
    provider_name: str | None = None,
    model_override: str | None = None,
) -> None:
    """Wiring: Provider + BashExecutor + TurnLoopUseCase."""
    state = AgentState()
    llm = _create_provider(provider_name)
    executor = _create_tool_executor()
    use_case = TurnLoopUseCase(llm_provider=llm, tool_executor=executor)

    tool_defs = [
        ToolDefinition(
            name="bash",
            description="Execute a bash command",
            parameters={"command": {"type": "string"}},
        ),
        ToolDefinition(
            name="read",
            description="Read a file from disk",
            parameters={"path": {"type": "string"}},
        ),
        ToolDefinition(
            name="write",
            description="Write content to a file",
            parameters={
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
        ),
    ]

    model = model_override or _default_model_for_provider(provider_name)

    result = await use_case.execute(
        state=state,
        text=prompt,
        model=model,
        tools=tool_defs,
    )

    for msg in result.assistant_messages:
        click.echo(msg.text)


def _default_model_for_provider(provider_name: str | None) -> str:
    """Return a sensible default model for the active provider."""
    if provider_name == "anthropic":
        return "claude-sonnet-4-20250514"
    if provider_name == "openai":
        return "gpt-4o"
    return "echo"
