# How to run pyagent

## Requirements

- Python 3.14+
- One API key: OpenRouter **or** Kimi (see below)

## Setup

```bash
python3.14 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## API keys

pyagent picks its provider from the environment, OpenRouter first:

| Key | Endpoint | Default model |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | `openrouter.ai/api/v1` | `moonshotai/kimi-k2` |
| `KIMI_API_KEY` | `api.moonshot.ai/v1` | `kimi-k2-0711-preview` |

```bash
# Option 1: OpenRouter — get a key at https://openrouter.ai/keys
export OPENROUTER_API_KEY="sk-or-..."

# Option 2: Kimi platform (pay-as-you-go) — create a key in the Kimi Platform console
export KIMI_API_KEY="sk-..."
```

Notes:

- If both are set, OpenRouter wins. `unset OPENROUTER_API_KEY` to force Kimi.
- On OpenRouter, account data-policy settings (e.g. enforced ZDR) can silently
  remove models that lack compliant tool-calling endpoints — if you see a 404,
  try another model with `-m`.
- A **Kimi Code membership** key is different: it uses
  `https://api.kimi.com/coding/v1` and model `kimi-for-coding`. Create/manage
  keys in the Kimi Code Console (members get up to 5, shown once). Wire it in
  via `-m` and `llm.py`'s endpoint constants if you use this kind of key.

## Run

```bash
.venv/bin/pyagent "explain this repo"
# or, after `source .venv/bin/activate`:
pyagent "add a docstring to tools.py"
pyagent -m openai/gpt-4o "write a haiku into poem.txt"
```

Text streams as it arrives; tool calls print as `▶ bash: ls -la` with a
one-line result; token usage prints at the end of each turn.

## Test

```bash
.venv/bin/pytest
```

15 tests: the SSE reducer, the three tool executors, and one end-to-end
agent loop against a fake provider (no network, no key needed).
