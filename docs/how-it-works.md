# How py-coding-agent Works

A step-by-step walkthrough of the architecture, from the moment you type a command at the shell until the agent responds.

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Clean Architecture Layers](#2-clean-architecture-layers)
3. [End-to-End: Running a Command](#3-end-to-end-running-a-command)
4. [The Turn Loop Explained](#4-the-turn-loop-explained)
5. [Tool Calling Flow](#5-tool-calling-flow)
6. [Message Types and State Machine](#6-message-types-and-state-machine)
7. [Domain Events](#7-domain-events)
8. [Component Reference](#8-component-reference)

---

## 1. System Architecture Overview

```
User types: py-agent print "bash:echo hello"
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: Framework & Drivers (CLI)                                          │
│ Parses arguments, wires all layers together, prints output                 │
│ File: cli/main.py                                                           │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: Adapters                                                           │
│ Converts between application commands and the outside world                │
│ RuleProvider      → parses "bash:" into a tool call                        │
│ BashExecutor      → runs actual shell commands via asyncio subprocess      │
│ FileSystemExecutor → reads/writes files via pathlib                       │
│ DispatcherToolExecutor → routes tool calls by name                         │
│ Files: adapters/*.py                                                        │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: Application (Use Cases)                                            │
│ Orchestrates domain objects to accomplish user goals                       │
│ TurnLoopUseCase   → loops: prompt → tools → results → repeat               │
│ PromptUseCase     → sends user message, receives assistant response        │
│ ExecuteToolUseCase → runs one tool call, appends result                    │
│ Files: application/*.py                                                     │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: Ports (Interfaces)                                                 │
│ Abstract contracts between application and adapters                        │
│ LLMProvider     → stream(model, messages, tools) → StreamEvent iterator    │
│ ToolExecutor    → execute(tool_call) → ToolExecutionResult                 │
│ Files: ports/*.py                                                           │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: Domain (Entities & Value Objects)                                  │
│ Pure business logic. No framework imports. No I/O. Immutable.              │
│ AgentState      → the aggregate root that protects conversation invariants │
│ Message types   → UserMessage, AssistantMessage, ToolResultMessage         │
│ Value objects   → MessageId, ToolCallId, ToolCall, ToolDefinition          │
│ Domain events   → MessageAppended, ToolResultAppended                      │
│ Files: domain/*.py                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Dependency Rule

**Source code dependencies point ONLY inward.**

- `domain/` knows nothing about `application/`, `ports/`, `adapters/`, or `cli/`
- `application/` depends on `domain/` and `ports/`
- `ports/` depends on `domain/`
- `adapters/` depends on `ports/` and `domain/`
- `cli/` is the only file that imports from all layers

---

## 2. Clean Architecture Layers

### Layer 1: Domain (The Heart)

The domain contains the **ubiquitous language** of the system. These are the concepts that exist independently of any framework or database.

**Key objects:**

| Object | Type | What it represents |
|--------|------|--------------------|
| `MessageId` | Value Object | Unique identifier for any message (UUID) |
| `ToolCallId` | Value Object | Unique identifier for a tool call request (UUID) |
| `ToolCall` | Value Object | Assistant's request: "please run tool X with args Y" |
| `ToolDefinition` | Value Object | Schema: tool name, description, parameter JSON schema |
| `UserMessage` | Value Object | Something the user typed |
| `AssistantMessage` | Value Object | LLM's response, may include tool calls |
| `ToolResultMessage` | Value Object | Result of executing a tool call |
| `AgentState` | Aggregate Root | The entire conversation + invariant enforcement |

**Invariants enforced by AgentState:**

```python
# OK: tool result follows a requested tool call
state.append_assistant_message(AssistantMessage(
    text="", tool_calls=(ToolCall(id=tc_id, name="read", arguments={"path": "/etc/hosts"}),)
))
state.append_tool_result(ToolResultMessage(tool_call_id=tc_id, content="127.0.0.1"))

# ERROR: ValueError — no pending tool call with this id
state.append_tool_result(ToolResultMessage(tool_call_id=ToolCallId(), content="orphan"))
```

**Why this matters:** The domain does not care whether the tool call came from OpenAI, Anthropic, or a hardcoded rule. It only knows that a tool result must match a pending tool call. This invariant is protected regardless of which adapter is wired in.

### Layer 2: Ports (Contracts)

Ports define what the application needs from the outside world, without specifying who provides it.

```python
# What the application asks for:
class LLMProvider(Protocol):
    def stream(self, *, model, messages, tools, system_prompt) -> AsyncIterator[StreamEvent]: ...

class ToolExecutor(Protocol):
    async def execute(self, tool_call: ToolCall) -> ToolExecutionResult: ...
```

**Key insight:** These are `Protocol`s (structural subtyping), not abstract base classes. Any object with the right methods satisfies the contract. No inheritance required.

### Layer 3: Application (Use Cases)

Each use case represents one complete user goal.

**PromptUseCase:**
```
Input:  state, user_text, model, tools, system_prompt
Output: PromptResult(assistant_message, events)

Steps:
1. Append UserMessage to state
2. Stream from LLMProvider
3. Collect TextChunks into a string
4. Collect ToolCallChunks into a tuple
5. Build AssistantMessage(text, tool_calls)
6. Append AssistantMessage to state
7. Return the assistant message + all domain events
```

**ExecuteToolUseCase:**
```
Input:  state, tool_call_id
Output: ExecuteToolResult(tool_result, events)

Steps:
1. Find ToolCall in the last assistant message matching tool_call_id
2. Execute via ToolExecutor
3. Build ToolResultMessage(tool_call_id, content, is_error)
4. Append ToolResultMessage to state (invariant check happens here)
5. Return the tool result + all domain events
```

**TurnLoopUseCase:**
```
Input:  state, text, model, tools, system_prompt
Output: TurnResult(assistant_messages, events)

Steps:
1. Run PromptUseCase → get assistant message
2. If assistant message has tool calls:
   a. Execute each tool call via ExecuteToolUseCase
   b. Re-prompt (empty user text, tool results are now in state)
   c. Go to step 1
3. If no tool calls, we are done
```

### Layer 4: Adapters (Concrete Implementations)

**RuleProvider** — the "brain" in the demo:

```
User: "bash:echo hello"     → yields ToolCallChunk(name="bash", arguments={"command": "echo hello"})
User: "read:/etc/hosts"     → yields ToolCallChunk(name="read", arguments={"path": "/etc/hosts"})
User: "write:/tmp/a.txt:hello" → yields ToolCallChunk(name="write", arguments={"path": ..., "content": ...})
User: "Hello world"         → yields TextChunk("Echo: Hello world")
Last message is ToolResult   → yields TextChunk("Done. Result: ...")
```

**BashExecutor** — runs shell commands:
```python
async def execute(tool_call):
    process = await asyncio.create_subprocess_shell("echo hello", ...)
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        return ToolExecutionResult(content=stderr, is_error=True)
    return ToolExecutionResult(content=stdout, is_error=False)
```

**FileSystemExecutor** — reads and writes files:
```python
async def execute(tool_call):
    if tool_call.name == "read":
        return ToolExecutionResult(content=Path(path).read_text())
    if tool_call.name == "write":
        Path(path).write_text(content)
        return ToolExecutionResult(content=f"Wrote {path}")
```

**DispatcherToolExecutor** — routes by name:
```python
async def execute(tool_call):
    executor = self._executors[tool_call.name]  # "bash" → BashExecutor, etc.
    return await executor.execute(tool_call)
```

### Layer 5: CLI (Composition Root)

The only file that imports from all layers. It is the **composition root**.

```python
async def _run_print(prompt: str):
    # Domain
    state = AgentState()

    # Ports: injected with concrete adapters
    llm = RuleProvider()
    executor = DispatcherToolExecutor(
        executors={
            "bash": BashExecutor(),
            "read": FileSystemExecutor(cwd="."),
            "write": FileSystemExecutor(cwd="."),
        }
    )

    # Application: use cases composed
    use_case = TurnLoopUseCase(llm_provider=llm, tool_executor=executor)

    # Run
    result = await use_case.execute(state=state, text=prompt, tools=tools)

    # Output
    for msg in result.assistant_messages:
        click.echo(msg.text)
```

---

## 3. End-to-End: Running a Command

Let's trace what happens when you type:

```bash
py-agent print "bash:echo hello"
```

### Step 1: Shell → CLI

```
$ py-agent print "bash:echo hello"
```

- `py-agent` is a console script defined in `pyproject.toml`
- It calls `py_coding_agent.cli.main:main()`
- `main()` calls `app()`, which is a `click.group()`
- `click` dispatches to the `print` subcommand
- `print_command("bash:echo hello")` runs `asyncio.run(_run_print("bash:echo hello"))`

### Step 2: Composition Root Wires Everything

```python
state = AgentState()                          # fresh conversation
llm = RuleProvider()                          # deterministic "brain"
executor = DispatcherToolExecutor(...)        # routes tools
use_case = TurnLoopUseCase(llm, executor)     # orchestrator
```

### Step 3: TurnLoopUseCase Executes

```python
result = await use_case.execute(
    state=state,
    text="bash:echo hello",
    tools=[bash_tool_def, read_tool_def, write_tool_def],
)
```

### Step 4: First PromptUseCase Run

```python
# Inside PromptUseCase.execute()
# 1. Append user message
events.extend(state.append_user_message(UserMessage(text="bash:echo hello")))

# State now: [UserMessage("bash:echo hello")]

# 2. Stream from LLM (RuleProvider)
async for event in llm.stream(model="rule", messages=state.messages, ...):
    ...
```

**RuleProvider sees:** `UserMessage("bash:echo hello")`

The text starts with `bash:`, so it parses the command:

```python
command = "echo hello"  # everything after "bash:"
tool_call = ToolCall(
    id=ToolCallId(),
    name="bash",
    arguments={"command": "echo hello"},
)
yield ToolCallChunk(tool_call=tool_call)
yield StopEvent(reason="tool_calls")
```

**PromptUseCase collects:**
- `text_parts = []` (no TextChunks)
- `tool_calls = [ToolCall(id=..., name="bash", arguments={"command": "echo hello"})]`

```python
assistant = AssistantMessage(text="", tool_calls=(tool_call,))
events.extend(state.append_assistant_message(assistant))

# State now: [UserMessage, AssistantMessage(tool_calls=(bash_call,))]
```

### Step 5: TurnLoop Detects Tool Calls

```python
while result.assistant_message.tool_calls:  # True! One tool call.
```

### Step 6: ExecuteToolUseCase Runs

```python
await execute_tool_use_case.execute(state=state, tool_call_id=tool_call.id)
```

**Inside ExecuteToolUseCase:**

```python
# 1. Find the ToolCall
for msg in reversed(state.messages):
    if isinstance(msg, AssistantMessage):
        for tc in msg.tool_calls:
            if tc.id == tool_call_id:
                tool_call = tc  # Found: bash tool call

# 2. Execute via DispatcherToolExecutor
result = await executor.execute(tool_call)
# Dispatcher routes "bash" → BashExecutor
# BashExecutor runs: asyncio.create_subprocess_shell("echo hello", ...)
# stdout = "hello\n"
# Returns: ToolExecutionResult(content="hello", is_error=False)

# 3. Build and append result
tool_result = ToolResultMessage(
    tool_call_id=tool_call_id,
    content="hello",
    is_error=False,
)
events = state.append_tool_result(tool_result)
# Invariant check: tool_call_id is in pending_tool_call_ids ✓

# State now: [UserMessage, AssistantMessage(tool_call), ToolResultMessage("hello")]
```

### Step 7: Re-Prompt with Tool Results

```python
# Back in TurnLoopUseCase
result = await prompt_use_case.execute(state=state, text="", ...)
```

**Inside PromptUseCase:**

```python
# text="" (empty) → skip user append
# Stream from RuleProvider with messages including tool result
```

**RuleProvider sees:** Last message is `ToolResultMessage(content="hello")`

```python
yield TextChunk(text="Done. Result: hello")
yield StopEvent(reason="stop")
```

**PromptUseCase collects:**
- `text_parts = ["Done. Result: hello"]`
- `tool_calls = []` (no tool calls)

```python
assistant = AssistantMessage(text="Done. Result: hello", tool_calls=())
state.append_assistant_message(assistant)

# State now:
# [UserMessage, AssistantMessage(tool), ToolResultMessage, AssistantMessage("Done. Result: hello")]
```

### Step 8: TurnLoop Detects No More Tool Calls

```python
while result.assistant_message.tool_calls:  # False! Empty tuple.
    # Exit loop
```

### Step 9: Return to CLI, Print Output

```python
# TurnLoopUseCase returns:
TurnResult(
    assistant_messages=[
        AssistantMessage(text="", tool_calls=(bash_call,)),
        AssistantMessage(text="Done. Result: hello", tool_calls=()),
    ],
    events=[MessageAppended, ToolResultAppended, MessageAppended, ...],
)

# CLI prints:
for msg in result.assistant_messages:
    click.echo(msg.text)

# Output:
# (empty line from first assistant message with no text)
# Done. Result: hello
```

### Final State

```python
[
    UserMessage(text="bash:echo hello"),
    AssistantMessage(text="", tool_calls=(ToolCall(id=..., name="bash", args={"command": "echo hello"}),)),
    ToolResultMessage(tool_call_id=..., content="hello", is_error=False),
    AssistantMessage(text="Done. Result: hello", tool_calls=()),
]
```

---

## 4. The Turn Loop Explained

A "turn" is one complete interaction cycle. It can be simple or involve multiple LLM calls.

### Simple Turn (no tools)

```
User: "Hello"
  └── PromptUseCase
        └── LLM: "Hello, how can I help?"
              └── Done
```

One LLM call, one response.

### Tool Turn (single tool)

```
User: "bash:pwd"
  └── PromptUseCase
        └── LLM: [ToolCall: bash {command: "pwd"}]
              ├── ExecuteToolUseCase → BashExecutor → "/workspace/py"
              └── Re-prompt (with tool result in context)
                    └── LLM: "Done. Result: /workspace/py"
                          └── Done
```

Two LLM calls: first requests the tool, second responds to the result.

### Multi-Tool Turn

```
User: "bash:date && bash:whoami"
  └── PromptUseCase
        └── LLM: [ToolCall: bash {command: "date"}, ToolCall: bash {command: "whoami"}]
              ├── ExecuteToolUseCase → date → result1
              ├── ExecuteToolUseCase → whoami → result2
              └── Re-prompt (with both results in context)
                    └── LLM: "Done. Results: ..."
                          └── Done
```

Two tools executed before the re-prompt.

### Nested Tool Turn

```
User: "bash:date"
  └── PromptUseCase
        └── LLM: [ToolCall: bash {command: "date"}]
              ├── ExecuteToolUseCase → "Tue May 10..."
              └── Re-prompt (with date result)
                    └── LLM: "bash:whoami" (asks for another tool)
                          ├── ExecuteToolUseCase → "node"
                          └── Re-prompt (with whoami result)
                                └── LLM: "Done."
                                      └── Done
```

The LLM can chain tools indefinitely. The loop exits when the assistant's response contains no tool calls.

---

## 5. Tool Calling Flow

### What is a Tool Call?

A tool call is the LLM's way of saying **"I cannot do this myself — please run this function for me and give me the result."**

It is structured data, not free text:

```python
ToolCall(
    id=ToolCallId(),           # "request #123"
    name="bash",               # which tool
    arguments={                # arguments
        "command": "echo hello"
    },
)
```

### Tool Definition (Schema)

Before the LLM can request a tool, it must know the tool exists and what arguments it takes:

```python
ToolDefinition(
    name="bash",
    description="Execute a shell command",
    parameters={
        "command": {"type": "string", "description": "The command to run"}
    },
)
```

### The Tool Call Lifecycle

```
1. TOOL DEFINITION (static)
   CLI registers ToolDefinition with TurnLoopUseCase
   TurnLoopUseCase passes it to PromptUseCase
   PromptUseCase passes it to LLMProvider stream()

2. TOOL REQUEST (LLM decides)
   LLM sees the tool definition in the system prompt
   LLM decides it needs to run a command
   LLM yields: ToolCallChunk(tool_call=ToolCall(name="bash", ...))

3. TOOL EXECUTION (adapter runs it)
   TurnLoopUseCase detects tool_calls in AssistantMessage
   ExecuteToolUseCase finds the matching ToolCall
   DispatcherToolExecutor routes to BashExecutor
   BashExecutor runs: asyncio.create_subprocess_shell("echo hello")
   Result: "hello"

4. TOOL RESULT (fed back to LLM)
   ExecuteToolUseCase builds ToolResultMessage(content="hello")
   Appends to AgentState (invariant: must match pending tool call)

5. LLM RESPONSE (with context)
   Re-prompt includes the tool result in message history
   LLM sees: [User, Assistant(tool), ToolResult("hello")]
   LLM yields: TextChunk("Done. Result: hello")
   No more tool calls → loop exits
```

### Why This Design?

- **Separation:** The LLM never runs code directly. It only *requests* that code be run.
- **Safety:** The `DispatcherToolExecutor` controls which tools are available. You can disable `bash` entirely.
- **Testability:** `FakeToolExecutor` returns programmed results without touching the filesystem.
- **Auditability:** Every tool call and result is recorded in `AgentState.messages`.

---

## 6. Message Types and State Machine

### The Three Message Roles

```python
@dataclass(frozen=True)
class UserMessage:
    text: str          # what the user typed
    role: "user"       # always "user"

@dataclass(frozen=True)
class AssistantMessage:
    text: str                        # response text (may be empty)
    tool_calls: tuple[ToolCall, ...] # optional tool requests
    role: "assistant"                # always "assistant"

@dataclass(frozen=True)
class ToolResultMessage:
    tool_call_id: ToolCallId    # links to the ToolCall that produced this
    content: str                 # output of the tool
    is_error: bool               # whether the tool failed
    role: "tool"                 # always "tool"
```

### Conversation Patterns

**Simple chat:**
```
[UserMessage("Hi")]
[AssistantMessage("Hello")]
```

**With tool call:**
```
[UserMessage("bash:pwd")]
[AssistantMessage("", tool_calls=(bash_call,))]
[ToolResultMessage("/workspace/py")]
[AssistantMessage("Done. Result: /workspace/py")]
```

**Multiple tools in one turn:**
```
[UserMessage("read a and read b")]
[AssistantMessage("", tool_calls=(read_a, read_b))]
[ToolResultMessage("content a")]
[ToolResultMessage("content b")]
[AssistantMessage("Both files read.")]
```

### The Pending Tool Call Invariant

AgentState tracks which tool calls have not yet received results:

```python
pending_tool_call_ids: set[ToolCallId]
```

Rules:
1. When an `AssistantMessage` with tool calls is appended, their IDs are added to `pending`
2. When a `ToolResultMessage` is appended, its ID must be in `pending`
3. After appending, the ID is removed from `pending`

```python
state.append_assistant_message(msg_with_tools)
# pending = {tc_id1, tc_id2}

state.append_tool_result(result_for_tc_id1)
# pending = {tc_id2}

state.append_tool_result(result_for_tc_id2)
# pending = set()

state.append_tool_result(result_for_tc_id3)  # ValueError!
```

This guarantees: **you can never have a dangling tool result.** The conversation is always valid.

---

## 7. Domain Events

Events are immutable records of what happened in the domain.

### Why Events?

- **Decoupling:** Use cases do not need to know about logging, persistence, or UI updates
- **Audit trail:** Every state change is recorded
- **Extension hooks:** Future extensions can subscribe to events

### Current Events

```python
@dataclass(frozen=True)
class MessageAppended(DomainEvent):
    message: Message  # the message that was added

@dataclass(frozen=True)
class ToolResultAppended(DomainEvent):
    message: ToolResultMessage  # the tool result that completed a cycle
```

### Event Flow

```
AgentState.append_user_message(msg)
  → records MessageAppended(msg)
  → returns [MessageAppended]
    → PromptUseCase collects it
      → TurnLoopUseCase aggregates all events
        → Future: EventPublisher could log/persist them
```

### Draining Events

Events are collected once and cleared:

```python
events = state.collect_events()  # returns all uncollected events
events = state.collect_events()  # returns [] — already drained
```

This prevents duplicate processing.

---

## 8. Component Reference

### Quick Lookup Table

| You want to... | Look at... |
|----------------|-----------|
| Add a new message type | `domain/message.py` |
| Change conversation rules | `domain/agent_state.py` |
| Add a new LLM provider | Implement `ports/llm_provider.py` Protocol |
| Add a new tool | Implement `ports/tool_executor.py` Protocol, register in dispatcher |
| Change how the CLI works | `cli/main.py` |
| Add a new use case | `application/` |
| Understand the test pattern | `tests/unit/fakes/` |

### Where to Make Changes

| Change | Files to modify |
|--------|----------------|
| Support OpenAI API | Create `adapters/openai_provider.py` |
| Support Claude API | Create `adapters/anthropic_provider.py` |
| Add `edit` tool | Create `adapters/edit_executor.py`, add to dispatcher |
| Persist sessions | Create `ports/session_store.py`, `adapters/json_session_store.py` |
| Add interactive TUI | Create `cli/tui.py` using `textual` |
| Add `/login` command | Create `adapters/env_auth_resolver.py` |

---

## Summary

The system works by **orchestrating a conversation state machine** across four layers:

1. **Domain** holds the truth: messages, invariants, events
2. **Ports** define contracts: what adapters must provide
3. **Application** orchestrates: prompt → tools → results → repeat
4. **Adapters** do the work: parse commands, run code, read files
5. **CLI** wires it all together for a specific runtime mode

To add a real LLM, you write **one file** implementing the `LLMProvider` Protocol. Everything else stays the same. That is the power of Clean Architecture.
