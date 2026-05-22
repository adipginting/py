"""OpenAIProvider adapter: streaming LLM completions via OpenAI's chat API."""

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
class _PendingToolCall:
    """Internal accumulator for tool call fragments across SSE chunks."""

    id: str = ""
    name: str = ""
    arguments: str = ""


def _message_to_openai(msg: Message) -> dict[str, Any]:
    """Convert a domain Message to the OpenAI chat message format."""
    if isinstance(msg, UserMessage):
        return {"role": "user", "content": msg.text}
    if isinstance(msg, AssistantMessage):
        if msg.tool_calls:
            tool_calls = [
                {
                    "id": tc.id.value,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments),
                    },
                }
                for tc in msg.tool_calls
            ]
            return {
                "role": "assistant",
                "content": msg.text or None,
                "tool_calls": tool_calls,
            }
        return {"role": "assistant", "content": msg.text}
    if isinstance(msg, ToolResultMessage):
        return {
            "role": "tool",
            "tool_call_id": msg.tool_call_id.value,
            "content": msg.content,
        }
    raise ValueError(f"Unknown message type: {type(msg)}")


def _build_request_body(
    model: str,
    messages: list[Message],
    tools: list[ToolDefinition],
    system_prompt: str,
) -> dict[str, Any]:
    """Construct the JSON body for the OpenAI chat completions endpoint."""
    openai_messages: list[dict[str, Any]] = []
    if system_prompt:
        openai_messages.append({"role": "system", "content": system_prompt})
    openai_messages.extend(_message_to_openai(m) for m in messages)

    body: dict[str, Any] = {
        "model": model,
        "messages": openai_messages,
        "stream": True,
    }

    if tools:
        body["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": {
                        "type": "object",
                        "properties": t.parameters,
                    },
                },
            }
            for t in tools
        ]

    return body


async def _parse_openai_sse(lines: AsyncIterator[str]) -> AsyncIterator[StreamEvent]:
    """Parse an OpenAI-style SSE stream into domain StreamEvents.

    Args:
        lines: An async iterator of SSE lines (e.g. from httpx.Response.aiter_lines).

    Yields:
        TextChunk, ToolCallChunk, UsageEvent, and StopEvent.
    """
    pending: dict[int, _PendingToolCall] = {}

    async for line in lines:
        line = line.strip()
        if not line or not line.startswith("data: "):
            continue

        data = line[6:]
        if data == "[DONE]":
            yield StopEvent(reason="stop")
            return

        try:
            payload: dict[str, Any] = json.loads(data)
        except json.JSONDecodeError:
            continue

        choices = payload.get("choices", [])
        if not choices:
            # Usage-only payload (non-streaming style, but handle just in case)
            usage = payload.get("usage")
            if usage:
                yield UsageEvent(
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                )
            continue

        delta = choices[0].get("delta", {})

        # Text content
        content = delta.get("content")
        if content:
            yield TextChunk(text=content)

        # Tool call deltas
        tool_call_deltas = delta.get("tool_calls")
        if tool_call_deltas:
            for tcd in tool_call_deltas:
                index: int = tcd.get("index", 0)
                ptc = pending.setdefault(index, _PendingToolCall())

                if "id" in tcd:
                    ptc.id = tcd["id"]
                function = tcd.get("function", {})
                if "name" in function:
                    ptc.name = function["name"]
                if "arguments" in function:
                    ptc.arguments += function["arguments"]

        # Finish reason
        finish_reason = choices[0].get("finish_reason")
        if finish_reason:
            if finish_reason == "tool_calls" and pending:
                for ptc in pending.values():
                    try:
                        args = json.loads(ptc.arguments) if ptc.arguments else {}
                    except json.JSONDecodeError:
                        args = {}
                    yield ToolCallChunk(
                        tool_call=ToolCall(
                            id=ToolCallId.from_string(ptc.id),
                            name=ptc.name,
                            arguments=args,
                        )
                    )
                yield StopEvent(reason="tool_calls")
                return
            # Normal stop or length/max_tokens/etc.
            if pending:
                for ptc in pending.values():
                    try:
                        args = json.loads(ptc.arguments) if ptc.arguments else {}
                    except json.JSONDecodeError:
                        args = {}
                    yield ToolCallChunk(
                        tool_call=ToolCall(
                            id=ToolCallId.from_string(ptc.id),
                            name=ptc.name,
                            arguments=args,
                        )
                    )
            yield StopEvent(reason=finish_reason)
            return

        # Usage can appear alongside the final delta in some streaming modes
        usage = payload.get("usage")
        if usage:
            yield UsageEvent(
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
            )

    # If stream ends without [DONE] or explicit finish_reason
    if pending:
        for ptc in pending.values():
            try:
                args = json.loads(ptc.arguments) if ptc.arguments else {}
            except json.JSONDecodeError:
                args = {}
            yield ToolCallChunk(
                tool_call=ToolCall(
                    id=ToolCallId.from_string(ptc.id),
                    name=ptc.name,
                    arguments=args,
                )
            )
    yield StopEvent(reason="stop")


class OpenAIProvider:
    """Adapter for OpenAI's chat completions streaming API."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
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
        """Stream completion events from OpenAI.

        Args:
            model: The OpenAI model ID (e.g. "gpt-4o").
            messages: The conversation history.
            tools: Available tools for the assistant.
            system_prompt: The system prompt to prepend.

        Yields:
            StreamEvent: Normalized domain events from the OpenAI SSE stream.
        """
        body = _build_request_body(model, messages, tools, system_prompt)
        response = await self._http.post(
            f"{self._base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        response.raise_for_status()

        try:
            async for event in _parse_openai_sse(response.aiter_lines()):
                yield event
        finally:
            if self._owns_client:
                await self._http.aclose()
