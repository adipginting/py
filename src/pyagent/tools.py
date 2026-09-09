"""Tools: each one is a JSON schema plus an async executor function.

Executors always return a string — either the output or an "Error: ..."
message — so a failing tool becomes context for the model instead of a
crash in the agent loop.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BASH_TIMEOUT_SECONDS = 30
MAX_OUTPUT_CHARS = 30_000


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    execute: Callable[..., Awaitable[str]]

    def schema(self) -> dict[str, Any]:
        """Wire-format tool definition for the chat completions API."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


async def read(path: str) -> str:
    try:
        return Path(path).read_text()
    except FileNotFoundError:
        return f"Error: no such file: {path}"
    except IsADirectoryError:
        return f"Error: not a file: {path}"
    except UnicodeDecodeError:
        return f"Error: not a text file: {path}"


async def write(path: str, content: str) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return f"Wrote {len(content)} characters to {path}"


async def bash(command: str) -> str:
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=BASH_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return f"Error: timed out after {BASH_TIMEOUT_SECONDS}s"

    output = stdout.decode(errors="replace") + stderr.decode(errors="replace")
    if process.returncode:
        output += f"[exit code {process.returncode}]"
    return _truncate(output.strip()) or "[no output]"


def _truncate(output: str) -> str:
    if len(output) <= MAX_OUTPUT_CHARS:
        return output
    return output[:MAX_OUTPUT_CHARS] + f"\n... [truncated: {len(output)} chars total]"


TOOLS: list[Tool] = [
    Tool(
        name="read",
        description="Read a text file and return its contents.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file."},
            },
            "required": ["path"],
        },
        execute=read,
    ),
    Tool(
        name="write",
        description="Write content to a file, creating parent directories as needed.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file."},
                "content": {"type": "string", "description": "Content to write."},
            },
            "required": ["path", "content"],
        },
        execute=write,
    ),
    Tool(
        name="bash",
        description=f"Run a shell command and return its output (times out after {BASH_TIMEOUT_SECONDS}s).",
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The shell command to run."},
            },
            "required": ["command"],
        },
        execute=bash,
    ),
]


async def execute_tool(
    name: str, arguments: dict[str, Any], tools: list[Tool] = TOOLS
) -> str:
    tool = next((t for t in tools if t.name == name), None)
    if tool is None:
        return f"Error: unknown tool: {name}"
    try:
        return await tool.execute(**arguments)
    except TypeError as error:
        return f"Error: bad arguments for {name}: {error}"
    except Exception as error:
        return f"Error: {name} failed: {error}"
