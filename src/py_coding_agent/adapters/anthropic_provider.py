"""AnthropicProvider adapter: streaming LLM completions via Anthropic's Messages API."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx

from py_coding_agent.domain.message import (
    AssistantMessage,
    Message,
    ToolResultMessage,
    UserMessage,
)
from py_coding_agent.domain.tool_call import ToolCall
from py_coding_agent.domain.tool_call_id import ToolCallId
from py_coding_agent.domain.tool_definition import ToolDefinition
from py_coding_agent.ports.llm_provider import (
    StopEvent,
    StreamEvent,
    TextChunk,
    ToolCallChunk,
    UsageEvent,
)


@dataclass
class _PendingContentBlock:
    """Internal accumulator for content block fragments across SSE events."""

    index: int
    block_type: str = ""
    text: str = ""
    tool_use_id: str = ""
    tool_name: str = ""
    tool_input_json: str = ""


def _message_to_anthropic(msg: Message) -> dict[str, Any]:
    """Convert a domain Message to the Anthropic message format."""
    if isinstance(msg, UserMessage):
        return {
            "role": "user",
            "content": [{"type": "text", "text": msg.text}],
        }
    if isinstance(msg, ToolResultMessage):
        return {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": msg.tool_call_id.value,
                    "content": msg.content,
                    "is_error": msg.is_error,
                }
            ],
        }
    if isinstance(msg, AssistantMessage):
        content: list[dict[str, Any]] = []
        if msg.text:
            content.append({"type": "text", "text": msg.text})
        for tc in msg.tool_calls:
            content.append(
                {
                    "type": "tool_use",
                    "id": tc.id.value,
                    "name": tc.name,
                    "input": tc.arguments,
                }
            )
        return {"role": "assistant", "content": content}
    raise ValueError(f"Unknown message type: {type(msg)}")


def _build_request_body(
    model: str,
    messages: list[Message],
    tools: list[ToolDefinition],
    system_prompt: str,
) -> dict[str, Any]:
    """Construct the JSON body for the Anthropic messages endpoint."""
    body: dict[str, Any] = {
        "model": model,
        "messages": [_message_to_anthropic(m) for m in messages],
        "max_tokens": 4096,
        "stream": True,
    }
    if system_prompt:
        body["system"] = system_prompt
    if tools:
        body["tools"] = [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": {
                    "type": "object",
                    "properties": t.parameters,
                },
            }
            for t in tools
        ]
    return body


async def _parse_anthropic_sse(lines: AsyncIterator[str]) -> AsyncIterator[StreamEvent]:
    """Parse an Anthropic-style SSE stream into domain StreamEvents.

    Args:
        lines: An async iterator of SSE lines.

    Yields:
        TextChunk, ToolCallChunk, UsageEvent, and StopEvent.
    """
    pending_blocks: dict[int, _PendingContentBlock] = {}
    current_event_type: str = ""
    input_tokens: int = 0

    async for line in lines:
        line = line.strip()
        if not line:
            current_event_type = ""
            continue

        if line.startswith("event: "):
            current_event_type = line[7:]
            continue

        if not line.startswith("data: "):
            continue

        data = line[6:]
        try:
            payload: dict[str, Any] = json.loads(data)
        except json.JSONDecodeError:
            continue

        event_type = payload.get("type", current_event_type)

        if event_type == "message_start":
            message = payload.get("message", {})
            usage = message.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)

        elif event_type == "content_block_start":
            index: int = payload.get("index", 0)
            block = payload.get("content_block", {})
            ptc = _PendingContentBlock(index=index, block_type=block.get("type", ""))
            if ptc.block_type == "tool_use":
                ptc.tool_use_id = block.get("id", "")
                ptc.tool_name = block.get("name", "")
            pending_blocks[index] = ptc

        elif event_type == "content_block_delta":
            index = payload.get("index", 0)
            delta = payload.get("delta", {})
            delta_type = delta.get("type", "")
            block = pending_blocks.get(index)
            if block is None:
                continue
            if delta_type == "text_delta":
                text = delta.get("text", "")
                if text:
                    yield TextChunk(text=text)
            elif delta_type == "input_json_delta":
                block.tool_input_json += delta.get("partial_json", "")

        elif event_type == "content_block_stop":
            index = payload.get("index", 0)
            block = pending_blocks.get(index)
            if block is None:
                continue
            if block.block_type == "tool_use":
                try:
                    tool_input = json.loads(block.tool_input_json) if block.tool_input_json else {}
                except json.JSONDecodeError:
                    tool_input = {}
                yield ToolCallChunk(
                    tool_call=ToolCall(
                        id=ToolCallId.from_string(block.tool_use_id),
                        name=block.tool_name,
                        arguments=tool_input,
                    )
                )

        elif event_type == "message_delta":
            delta = payload.get("delta", {})
            stop_reason = delta.get("stop_reason", "")
            usage = payload.get("usage", {})
            output_tokens = usage.get("output_tokens", 0)
            if input_tokens or output_tokens:
                yield UsageEvent(input_tokens=input_tokens, output_tokens=output_tokens)
            if stop_reason:
                yield StopEvent(reason=stop_reason)
                return

        elif event_type == "message_stop":
            if not input_tokens:
                yield StopEvent(reason="end_turn")
                return

    yield StopEvent(reason="end_turn")


class AnthropicProvider:
    """Adapter for Anthropic's Messages streaming API."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.anthropic.com/v1",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._http = http_client or httpx.AsyncClient()
        self._owns_client = http_client is None

    async def stream(
        self,
        *,
        model: str,
        messages: list[Message],
        tools: list[ToolDefinition],
        system_prompt: str,
    ) -> AsyncIterator[StreamEvent]:
        """Stream completion events from Anthropic.

        Args:
            model: The Anthropic model ID.
            messages: The conversation history.
            tools: Available tools for the assistant.
            system_prompt: The system prompt.

        Yields:
            StreamEvent: Normalized domain events from the Anthropic SSE stream.
        """
        body = _build_request_body(model, messages, tools, system_prompt)
        response = await self._http.post(
            f"{self._base_url}/messages",
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json=body,
        )
        response.raise_for_status()

        try:
            async for event in _parse_anthropic_sse(response.aiter_lines()):
                yield event
        finally:
            if self._owns_client:
                await self._http.aclose()
