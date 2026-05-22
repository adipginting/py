"""BashExecutor adapter: runs shell commands via asyncio subprocess."""

from __future__ import annotations

import asyncio

from py_coding_agent.domain.tool_call import ToolCall
from py_coding_agent.ports.tool_executor import ToolExecutionResult


class BashExecutor:
    """Execute bash commands using asyncio subprocess."""

    async def execute(self, tool_call: ToolCall) -> ToolExecutionResult:
        """Run the command from the tool call and return stdout or stderr."""
        command = tool_call.arguments.get("command", "")
        if not isinstance(command, str):
            return ToolExecutionResult(content="Invalid command argument", is_error=True)

        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            return ToolExecutionResult(
                content=stderr.decode("utf-8", errors="replace").strip(),
                is_error=True,
            )

        return ToolExecutionResult(
            content=stdout.decode("utf-8", errors="replace").strip(),
            is_error=False,
        )
