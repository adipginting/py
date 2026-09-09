# pyagent

A minimal coding agent you can read aloud: one provider, one loop, one
printer. You give it a prompt, it streams text from an LLM, calls tools
(`read`, `write`, `bash`), and prints everything as it happens.

```bash
export OPENROUTER_API_KEY="sk-or-..."
pip install -e .
pyagent "explain this repo"
```

```
▶ bash: ls -la
  → total 40
▶ read: pyproject.toml
  → [build-system]
This is pyagent, a minimal Python coding agent ...
[usage: 1033 in / 33 out]
```

## Design

![The agent loop, animated](docs/animation/agent-loop.gif)

Four modules under `src/pyagent/`:

| Module | Job |
| --- | --- |
| `llm.py` | Streams an OpenAI-compatible API (OpenRouter or Kimi), parses SSE into typed events |
| `agent.py` | `AgentHarness` — the prompt → tool-call → re-prompt loop; emits events, never prints |
| `tools.py` | Three tools, each a JSON schema plus an async function |
| `cli.py` | Print mode: subscribes to the event stream and renders it |

The one idea: **events are the contract**. The core yields `TextDelta` /
`ToolCallStarted` / `ToolResult` / `Usage` / `Done`; any frontend — the CLI,
a test, a future TUI — just subscribes.

No TUI, no sessions, no persistence, no provider catalog. That's the point.

## Docs

- [How to run](docs/how-to-run.md) — setup, API keys, commands
- [How it works](docs/how-it-works.md) — the architecture, module by module

## Tests

```bash
pip install -e ".[dev]"
pytest
```
