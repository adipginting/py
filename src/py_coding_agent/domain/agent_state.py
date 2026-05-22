"""AgentState aggregate root."""

from dataclasses import dataclass, field

from py_coding_agent.domain.events import (
    DomainEvent,
    MessageAppended,
    TokenUsageRecorded,
    ToolResultAppended,
)
from py_coding_agent.domain.message import (
    AssistantMessage,
    Message,
    ToolResultMessage,
    UserMessage,
)
from py_coding_agent.domain.token_usage import TokenUsage
from py_coding_agent.domain.tool_call_id import ToolCallId


@dataclass
class AgentState:
    """The aggregate root for agent conversation state.

    Protects invariants:
      - A ToolResultMessage must match a pending ToolCall.
      - Messages are append-only.
    """

    messages: list[Message] = field(default_factory=list)
    pending_tool_call_ids: set[ToolCallId] = field(default_factory=set)
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    _events: list[DomainEvent] = field(default_factory=list, repr=False)

    def _record(self, event: DomainEvent) -> None:
        self._events.append(event)

    def append_user_message(self, message: UserMessage) -> list[DomainEvent]:
        """Append a user message to the conversation."""
        self.messages.append(message)
        self._record(MessageAppended(message))
        return self.collect_events()

    def append_assistant_message(self, message: AssistantMessage) -> list[DomainEvent]:
        """Append an assistant message and track pending tool calls."""
        self.messages.append(message)
        self.pending_tool_call_ids.update(tc.id for tc in message.tool_calls)
        self._record(MessageAppended(message))
        return self.collect_events()

    def append_tool_result(self, message: ToolResultMessage) -> list[DomainEvent]:
        """Append a tool result, verifying it answers a pending tool call."""
        if message.tool_call_id not in self.pending_tool_call_ids:
            raise ValueError(f"No pending tool call with id {message.tool_call_id}")
        self.messages.append(message)
        self.pending_tool_call_ids.discard(message.tool_call_id)
        self._record(ToolResultAppended(message))
        return self.collect_events()

    def add_token_usage(self, usage: TokenUsage) -> list[DomainEvent]:
        """Add token usage to the running total and emit a domain event."""
        self.token_usage = self.token_usage + usage
        self._record(TokenUsageRecorded(usage))
        return self.collect_events()

    def collect_events(self) -> list[DomainEvent]:
        """Return and drain all uncollected events."""
        events = self._events[:]
        self._events.clear()
        return events
