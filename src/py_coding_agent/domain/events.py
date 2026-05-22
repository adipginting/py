"""Domain events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from py_coding_agent.domain.message import Message, ToolResultMessage
    from py_coding_agent.domain.token_usage import TokenUsage


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events."""

    pass


@dataclass(frozen=True)
class MessageAppended(DomainEvent):
    """A message was appended to the conversation."""

    message: Message


@dataclass(frozen=True)
class ToolResultAppended(DomainEvent):
    """A tool result was appended, completing a tool call cycle."""

    message: ToolResultMessage


@dataclass(frozen=True)
class TokenUsageRecorded(DomainEvent):
    """Token usage was recorded for a turn."""

    usage: TokenUsage
