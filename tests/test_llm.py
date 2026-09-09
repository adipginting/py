"""Tests for parse_sse — the stream-to-event reduction where silent bugs live."""

import json

from pyagent.llm import TextChunk, ToolCall, Usage, parse_sse


def sse(payload: dict) -> str:
    return "data: " + json.dumps(payload)


def chunk(delta: dict, finish_reason: str | None = None) -> dict:
    return {"choices": [{"delta": delta, "finish_reason": finish_reason}]}


async def fake_lines(*lines: str):
    for line in lines:
        yield line


async def collect(events):
    return [event async for event in events]


async def test_text_streams_through_as_chunks():
    events = await collect(parse_sse(fake_lines(
        sse(chunk({"content": "Hello"})),
        sse(chunk({"content": ", world"})),
        sse(chunk({}, finish_reason="stop")),
        "data: [DONE]",
    )))
    assert events == [TextChunk("Hello"), TextChunk(", world")]


async def test_tool_call_fragments_accumulate_into_one_call():
    events = await collect(parse_sse(fake_lines(
        sse(chunk({"tool_calls": [
            {"index": 0, "id": "call_1", "function": {"name": "bash", "arguments": '{"comm'}},
        ]})),
        sse(chunk({"tool_calls": [
            {"index": 0, "function": {"arguments": 'and": "echo'}},
        ]})),
        sse(chunk({"tool_calls": [
            {"index": 0, "function": {"arguments": ' hi"}'}},
        ]})),
        sse(chunk({}, finish_reason="tool_calls")),
        "data: [DONE]",
    )))
    assert events == [ToolCall(id="call_1", name="bash", arguments={"command": "echo hi"})]


async def test_parallel_tool_calls_emit_in_index_order():
    events = await collect(parse_sse(fake_lines(
        sse(chunk({"tool_calls": [
            {"index": 0, "id": "call_a", "function": {"name": "read", "arguments": '{"path": "a'}},
            {"index": 1, "id": "call_b", "function": {"name": "read", "arguments": '{"path": "b'}},
        ]})),
        sse(chunk({"tool_calls": [
            {"index": 0, "function": {"arguments": '.txt"}'}},
            {"index": 1, "function": {"arguments": '.md"}'}},
        ]})),
        sse(chunk({}, finish_reason="tool_calls")),
    )))
    assert events == [
        ToolCall(id="call_a", name="read", arguments={"path": "a.txt"}),
        ToolCall(id="call_b", name="read", arguments={"path": "b.md"}),
    ]


async def test_usage_event_is_forwarded():
    events = await collect(parse_sse(fake_lines(
        sse(chunk({"content": "hi"}, finish_reason="stop")),
        sse({"choices": [], "usage": {"prompt_tokens": 10, "completion_tokens": 3}}),
        "data: [DONE]",
    )))
    assert events == [TextChunk("hi"), Usage(input_tokens=10, output_tokens=3)]


async def test_junk_lines_are_skipped_and_stream_end_still_flushes():
    events = await collect(parse_sse(fake_lines(
        "",
        ": keep-alive comment",
        "data: {not json",
        sse(chunk({"tool_calls": [
            {"index": 0, "id": "call_1", "function": {"name": "bash", "arguments": '{"command": "ls"}'}},
        ]})),
    )))
    assert events == [ToolCall(id="call_1", name="bash", arguments={"command": "ls"})]


async def test_unparseable_arguments_become_empty_dict():
    events = await collect(parse_sse(fake_lines(
        sse(chunk({"tool_calls": [
            {"index": 0, "id": "call_1", "function": {"name": "bash", "arguments": "{oops"}},
        ]})),
        sse(chunk({}, finish_reason="tool_calls")),
    )))
    assert events == [ToolCall(id="call_1", name="bash", arguments={})]
