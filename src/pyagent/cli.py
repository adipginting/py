"""Print-mode CLI: `pyagent "prompt"` streams one agent run to the terminal."""

from __future__ import annotations

import asyncio
import json
import os
from functools import partial

import click
import httpx

from pyagent.agent import AgentHarness, Done, TextDelta, ToolCallStarted, ToolResult
from pyagent.llm import (
    DEFAULT_MODEL,
    KIMI_API_URL,
    KIMI_DEFAULT_MODEL,
    OPENROUTER_API_URL,
    Usage,
    stream_chat,
)


@click.command()
@click.argument("prompt_arg", metavar="PROMPT", required=False)
@click.option("-p", "--prompt", "prompt_option", help="Same as the PROMPT argument.")
@click.option("-m", "--model", default=None, help="Model (defaults to the provider's default).")
def main(prompt_arg: str | None, prompt_option: str | None, model: str | None) -> None:
    """Run the coding agent on PROMPT and print everything it does."""
    prompt = prompt_option or prompt_arg
    if not prompt:
        raise click.UsageError('a prompt is required: pyagent "list files here"')

    if api_key := os.environ.get("OPENROUTER_API_KEY"):
        api_url = OPENROUTER_API_URL
        model = model or DEFAULT_MODEL
    elif api_key := os.environ.get("KIMI_API_KEY"):
        api_url = KIMI_API_URL
        model = model or KIMI_DEFAULT_MODEL
    else:
        raise click.ClickException(
            "no API key — export OPENROUTER_API_KEY (https://openrouter.ai/keys)"
            " or KIMI_API_KEY (https://platform.moonshot.ai/)"
        )

    harness = AgentHarness(
        stream=partial(stream_chat, api_key=api_key, model=model, api_url=api_url)
    )
    try:
        asyncio.run(_print_events(harness, prompt))
    except httpx.HTTPStatusError as error:
        status = error.response.status_code
        raise click.ClickException(f"provider returned HTTP {status}") from error
    except httpx.HTTPError as error:
        raise click.ClickException(f"could not reach the provider: {error}") from error


async def _print_events(harness: AgentHarness, prompt: str) -> None:
    async for event in harness.run(prompt):
        if isinstance(event, TextDelta):
            print(event.text, end="", flush=True)
        elif isinstance(event, ToolCallStarted):
            detail = (
                event.arguments.get("command")
                or event.arguments.get("path")
                or json.dumps(event.arguments)
            )
            print(f"\n▶ {event.name}: {detail}")
        elif isinstance(event, ToolResult):
            first_line = event.output.splitlines()[0] if event.output else ""
            print(f"  → {first_line[:120]}")
        elif isinstance(event, Usage):
            print(f"\n[usage: {event.input_tokens} in / {event.output_tokens} out]")
        elif isinstance(event, Done):
            print()
