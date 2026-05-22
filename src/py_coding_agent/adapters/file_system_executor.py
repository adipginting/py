"""FileSystemExecutor adapter: read and write files."""

from __future__ import annotations

from pathlib import Path

from py_coding_agent.domain.tool_call import ToolCall
from py_coding_agent.ports.tool_executor import ToolExecutionResult


class FileSystemExecutor:
    """Execute filesystem tools: read, write."""

    def __init__(self, cwd: str = ".") -> None:
        self._cwd = Path(cwd).resolve()

    async def execute(self, tool_call: ToolCall) -> ToolExecutionResult:
        """Dispatch read and write operations."""
        name = tool_call.name
        arguments = tool_call.arguments

        if name == "read":
            return self._read(arguments)
        if name == "write":
            return self._write(arguments)

        return ToolExecutionResult(content=f"Unknown tool: {name}", is_error=True)

    def _read(self, arguments: dict[str, object]) -> ToolExecutionResult:
        path = self._resolve(arguments.get("path", ""))
        try:
            content = path.read_text()
            return ToolExecutionResult(content=content)
        except FileNotFoundError:
            return ToolExecutionResult(content=f"File not found: {path}", is_error=True)
        except PermissionError:
            return ToolExecutionResult(content=f"Permission denied: {path}", is_error=True)

    def _write(self, arguments: dict[str, object]) -> ToolExecutionResult:
        path = self._resolve(arguments.get("path", ""))
        content = arguments.get("content", "")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(content))
            return ToolExecutionResult(content=f"Wrote {path}")
        except PermissionError:
            return ToolExecutionResult(content=f"Permission denied: {path}", is_error=True)

    def _resolve(self, raw: object) -> Path:
        path = Path(str(raw))
        if path.is_absolute():
            return path
        return self._cwd / path
