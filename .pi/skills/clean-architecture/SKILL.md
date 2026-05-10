---
name: clean-architecture
description: Enforces Clean Architecture, Hexagonal Architecture, and Ports & Adapters principles. Use when designing layered software systems, separating business logic from frameworks, choosing abstractions, or reviewing dependency direction.
---

# Clean Architecture

Guide the user in applying Clean Architecture, Hexagonal Architecture (Ports & Adapters), and related layered patterns.

## Core Principles

1. **Independence of frameworks** — The business rules are not bound to any framework, library, or external tool.
2. **Testability** — Business rules can be tested without UI, database, web server, or any external element.
3. **Independence of UI** — The UI can change without changing the business rules.
4. **Independence of database** — Business rules are not bound to a specific database technology.
5. **Independence of external services** — Business rules do not know anything about the outside world.

## Dependency Rule

Source code dependencies must point only inward, toward higher-level policies. Nothing in an inner circle can know anything at all about something in an outer circle.

## Layered Structure (inner → outer)

1. **Entities** — Enterprise-wide business rules. Plain objects, no framework imports. Most stable.
2. **Use Cases** — Application-specific business rules. Orchestrate data flow to/from entities. Contain application logic, not business rules.
3. **Interface Adapters** — Convert data between use cases and external agents. Controllers, presenters, gateways, mappers.
4. **Frameworks & Drivers** — UI, web frameworks, database tools, external APIs. The most volatile layer.

## Rules

1. Never allow an inner layer to import or reference an outer layer. Never.
2. Use interfaces (ports) defined in the inner layers; implement them in outer layers (adapters).
3. Data structures crossing boundaries should be simple DTOs, not framework models.
4. Entities contain no database annotations, no ORM imports, no JSON serialization logic.
5. Use cases contain no HTTP status codes, no framework request/response types, no UI strings.
6. Framework code belongs in Frameworks & Drivers or Interface Adapters. If you find `import express` in a use case, that is a bug.
7. Prefer constructor injection. A use case declares its dependencies as interfaces; a composition root wires concrete adapters.
8. The composition root is the only place where all layers are referenced together. It is allowed to know everything.
9. Do not over-engineer. Not every system needs full Clean Architecture. Ask about scale, team size, and expected churn before prescribing layers.
10. If the user shows code, audit dependency direction first. Flag any import that violates the rule before reviewing anything else.

## Ports & Adapters (Hexagonal) Mapping

- **Inbound ports** (driving) = use case interfaces the outer world calls into (e.g., `CreateOrder`).
- **Outbound ports** (driven) = interfaces the inner world defines for outer infrastructure (e.g., `OrderRepository`, `PaymentGateway`).
- **Adapters** = concrete implementations of ports in outer layers.

## Workflow

1. Identify the core business rules (entities).
2. Define use cases that orchestrate those rules.
3. Define inbound ports (what the app does) and outbound ports (what the app needs).
4. Implement adapters in outer layers.
5. Write a composition root that wires it all together.
6. Verify: can you replace the database or web framework without touching entities or use cases?
