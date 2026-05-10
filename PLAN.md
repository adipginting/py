# py-coding-agent — Implementation Progress

**Repo:** `/workspace/py`

## Current Status

**18 commits, 58 tests, ~400 SLOC, 97%+ line coverage.**

All four Clean Architecture layers are populated and wired end-to-end. The CLI runs as `py-agent print <prompt>`.

---

## Commit History

| Commit | What |
|--------|------|
| `f6aced5` | Repository skeleton: pyproject.toml, ruff, mypy, pytest, CI workflow, layered package structure |
| `5a6089f` | `MessageId` value object (frozen UUID) |
| `d323760` | `ToolCallId` value object (frozen UUID) |
| `20cadfd` | `UserMessage`, `AssistantMessage`, `ToolResultMessage`, `ToolCall` |
| `aa797e5` | `AgentState` aggregate root with tool-result invariant |
| `955bbba` | Domain events: `MessageAppended`, `ToolResultAppended` |
| `9386a05` | `ToolDefinition` value object |
| `1fccc1d` | `LLMProvider` port with stream events, `FakeLLMProvider` |
| `7be2d56` | `PromptUseCase` — wire AgentState + LLMProvider |
| `b9d799e` | `ToolExecutor` port, `FakeToolExecutor` |
| `f215f21` | `ExecuteToolUseCase` — run tool + append result |
| `67ddf5a` | `TurnLoopUseCase` — prompt → tools → execute → re-prompt loop |
| `899bc24` | `EchoProvider` adapter (echoes last user message) |
| `85da8de` | `BashExecutor` adapter (asyncio subprocess) |
| `cadb126` | CLI `print` command with click |
| `691ee86` | Fix `main()` entrypoint for `py-agent` console script |
| `fe4cfc8` | `FileSystemExecutor` adapter (read/write via pathlib) |
| `b0e971b` | `DispatcherToolExecutor` — routes tools by name |

---

## What's Implemented

### Domain Layer (inner circle, pure Python)

| File | Lines | Responsibility |
|------|-------|----------------|
| `domain/message_id.py` | 25 | `MessageId` — frozen UUID wrapper |
| `domain/tool_call_id.py` | 25 | `ToolCallId` — frozen UUID wrapper |
| `domain/tool_call.py` | 17 | `ToolCall(id, name, arguments)` — assistant's request |
| `domain/tool_definition.py` | 18 | `ToolDefinition(name, description, parameters)` — schema |
| `domain/message.py` | 54 | `UserMessage`, `AssistantMessage`, `ToolResultMessage`, `Message` union |
| `domain/events.py` | 30 | `DomainEvent`, `MessageAppended`, `ToolResultAppended` |
| `domain/agent_state.py` | 59 | Aggregate root: append messages, enforce invariants, emit events |

**Invariants enforced:**
- `AgentState.messages` is append-only
- `ToolResultMessage` can only be appended if its `tool_call_id` matches a pending call
- Dangling tool results raise `ValueError`

### Ports Layer (interfaces)

| File | Lines | Responsibility |
|------|-------|----------------|
| `ports/llm_provider.py` | 75 | `LLMProvider` Protocol, stream event types (`TextChunk`, `ToolCallChunk`, `StopEvent`, etc.) |
| `ports/tool_executor.py` | 33 | `ToolExecutor` Protocol, `ToolExecutionResult`, `ToolExecutionInvocation` |

### Application Layer (use cases)

| File | Lines | Responsibility |
|------|-------|----------------|
| `application/prompt_use_case.py` | 91 | Send user message → stream LLM → collect response → append to state |
| `application/execute_tool_use_case.py` | 61 | Find pending tool call → execute → append result to state |
| `application/turn_loop_use_case.py` | 90 | Orchestrate full turn: prompt → (if tools) execute → re-prompt → repeat until stop |

### Adapters Layer (concrete implementations)

| File | Lines | Responsibility |
|------|-------|----------------|
| `adapters/echo_provider.py` | 31 | Echoes last user message as assistant response |
| `adapters/rule_provider.py` | 95 | Deterministic "brain": parses `bash:`, `read:`, `write:` prefixes into tool calls |
| `adapters/bash_executor.py` | 35 | Runs commands via `asyncio.create_subprocess_shell` |
| `adapters/file_system_executor.py` | 61 | `read` and `write` operations via `pathlib` |
| `adapters/dispatcher_tool_executor.py` | 20 | Routes tool calls by name to sub-executors |

### Fakes (test doubles)

| File | Lines | Responsibility |
|------|-------|----------------|
| `tests/unit/fakes/fake_llm_provider.py` | 55 | Programmable fake: yields preset events, records invocations |
| `tests/unit/fakes/fake_tool_executor.py` | 30 | Programmable fake: per-tool results, records invocations |

### CLI Layer (composition root)

| File | Lines | Responsibility |
|------|-------|----------------|
| `cli/main.py` | 53 | `click` group with `print` command. Wires RuleProvider + Dispatcher + TurnLoopUseCase. |

---

## How to Run

```bash
cd /workspace/py

# Install
pip install -e ".[dev]" --break-system-packages

# Run commands
py-agent print "Hello world"
py-agent print "bash:pwd"
py-agent print "bash:echo hello"
py-agent print "read:/etc/hostname"
py-agent print "write:/tmp/test.txt:hello world"

# Test
pytest              # 58 tests, all green
ruff check src tests
mypy src
```

---

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| `click` over `typer` | Typer's `CliRunner` had argument parsing issues with quoted strings. Click is explicit and battle-tested. |
| `dataclass` over `pydantic` in domain | Lower overhead for hot-path entities. Pydantic reserved for schemas/settings. |
| Hand-written fakes over `unittest.mock` | Fakes expose protocol contract violations that mocks hide. |
| `Protocol` for ports | Python 3.11 structural subtyping. No inheritance required. |
| `frozen=True` value objects | Immutability by default. Value equality and hashability for free. |
| `TYPE_CHECKING` for imports | Eliminates circular imports between domain modules. |

---

## What's Still Pending

### Phase 1: Domain Model (Complete)
- [x] Value Objects: `MessageId`, `ToolCallId`
- [x] Messages: `UserMessage`, `AssistantMessage`, `ToolResultMessage`
- [x] Tool Domain: `ToolCall`, `ToolDefinition`
- [x] Events: `DomainEvent`, `MessageAppended`, `ToolResultAppended`
- [x] Aggregate: `AgentState`
- [ ] `CustomMessage` — for extension integration
- [ ] `SessionId`, `Timestamp` value objects

### Phase 2: Application Use Cases (Partial)
- [x] `PromptUseCase`
- [x] `ExecuteToolUseCase`
- [x] `TurnLoopUseCase`
- [ ] `CompactSessionUseCase`
- [ ] `ExportSessionUseCase`

### Phase 3: Ports (Partial)
- [x] `LLMProvider`
- [x] `ToolExecutor`
- [ ] `SessionStore`
- [ ] `AuthResolver`
- [ ] `EventPublisher`
- [ ] `ResourceLoader`

### Phase 4: Adapters (Partial)
- [x] `EchoProvider`
- [x] `RuleProvider`
- [x] `BashExecutor`
- [x] `FileSystemExecutor`
- [x] `DispatcherToolExecutor`
- [ ] Edit tool (diff/patch based file modification)
- [ ] `OpenAIProvider` (or real LLM adapter)
- [ ] `InMemorySessionStore` / `JsonFileSessionStore`
- [ ] `EnvAuthResolver`

### Phase 5–9: Not Started
- [ ] Provider abstraction + unified streaming (OpenAI, Anthropic)
- [ ] Session persistence + compaction + branching
- [ ] Extensions + skills loading
- [ ] Interactive TUI with `textual`
- [ ] `rpc` mode for editor integration
- [ ] OAuth flows + `/login`
- [ ] Packaging + `pipx install`

---

## Next Priorities

1. **Real LLM adapter** — `OpenAIProvider` with SSE streaming via `httpx`
2. **Session persistence** — `JsonFileSessionStore` for conversation history
3. **TUI** — `textual` interactive mode
4. **Edit tool** — diff/patch based file modification
5. **Context management** — token counting, overflow detection, compaction trigger
