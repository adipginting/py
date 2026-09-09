# How pyagent works

pyagent is a minimal coding agent: you give it a prompt, it talks to an LLM,
calls tools, and prints everything as it happens. The whole thing is four
small modules under `src/pyagent/`, designed so each can be read aloud.

## The one idea: events are the contract

Nothing in the core prints, renders, or writes files for display. The agent
loop **yields typed events**, and whatever runs the agent — the CLI, a test,
a future TUI — subscribes and decides what to show.

```
cli.py  ──subscribes──▶  agent.py  ──streams from──▶  llm.py
(prints)                 (the loop, no I/O)            (OpenRouter, no printing)
                                │
                                └──calls──▶ tools.py (read / write / bash)
```

## The loop (`agent.py`)

`AgentHarness.run(prompt)` is the whole brain:

1. Append the user prompt to the message list (plain dicts, OpenAI wire format).
2. Stream one completion from the LLM, yielding `TextDelta` events as text arrives.
3. If the model asked for tool calls: yield `ToolCallStarted`, execute the tool,
   yield `ToolResult`, append the result to the messages, and go to step 2.
4. If the model asked for nothing: yield `Done` and stop.

A run is bounded by `MAX_ITERATIONS` (25), so a model that keeps calling
tools forever gets stopped instead of looping into the sunset.

## The provider (`llm.py`)

One endpoint per run, over the OpenAI-compatible chat completions API:
OpenRouter when `OPENROUTER_API_KEY` is set, Kimi direct
(`api.moonshot.ai`) when only `KIMI_API_KEY` is. `stream_chat` POSTs the
messages and tool schemas with `stream: true` and parses the
server-sent-events response.

The subtle part: tool calls don't arrive whole. The id, the name, and the
arguments stream in as fragments spread across many chunks, so `parse_sse`
accumulates them per call and emits one complete `ToolCall` each when the
stream ends. Text, by contrast, flows straight through as `TextChunk`s —
that's what makes the output feel live.

## The tools (`tools.py`)

A tool is just a JSON schema plus an async function that returns a string:

- `read(path)` — return a file's contents
- `write(path, content)` — write a file, creating parent directories
- `bash(command)` — run a shell command (30s timeout, output truncated at 30k chars)

Executors never raise: a failure comes back as an `"Error: ..."` string,
which becomes context for the model — it can see what went wrong and try
something else, instead of crashing the loop.

## The CLI (`cli.py`)

`pyagent "explain this repo"` — print mode only. It subscribes to the event
stream and renders it to the terminal: text streams token by token, tool
calls print as `▶ bash: ls -la`, results as a one-line summary, and token
usage at the end. It needs one thing: a key in the environment
(`OPENROUTER_API_KEY`, or `KIMI_API_KEY` for Kimi direct). Model defaults
to `moonshotai/kimi-k2`, overridable with `-m`.

## The tests

Deliberately thin, aimed where bugs hide:

- `test_llm.py` — the SSE reducer (fragments in, complete tool calls out)
- `test_tools.py` — the three executors, including their error paths
- `test_agent.py` — one end-to-end loop with a fake provider: model asks
  for a tool, tool runs, model answers, `Done`

The fake provider is the trick worth stealing: the harness takes its stream
function as a parameter, so tests drive the entire loop without any network.

## What pyagent doesn't do

No TUI, no sessions, no persistence, no provider catalog, no HTTP
server. That's not a roadmap — it's the point. One provider, one loop, one
printer.
