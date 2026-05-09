"""ToolDefinition value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolDefinition:
    """A named capability available to the agent.

    Describes what the tool does and the JSON schema of its parameters.
    """

    name: str
    description: str
    parameters: dict[str, Any]
