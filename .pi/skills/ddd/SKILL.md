---
name: ddd
description: Guides domain-driven design modeling and implementation. Use when designing bounded contexts, defining aggregates, entities, value objects, domain events, or refactoring toward a rich domain model.
---

# Domain-Driven Design (DDD)

Guide the user through domain-driven design concepts, modeling, and tactical implementation.

## Rules

1. Always start by identifying the core domain and ubiquitous language before structural decisions.
2. Distinguish clearly between strategic DDD (bounded contexts, context mapping) and tactical DDD (aggregates, entities, value objects, domain services).
3. Never model prematurely. Ask clarifying questions about invariants, business rules, and transaction boundaries first.
4. Demand invariants. An aggregate without invariants is a data bag.
5. Prefer value objects over entities where immutability and equality-by-value fit.
6. Be explicit about consistency boundaries. A single transaction should modify only one aggregate.
7. Use domain events for cross-aggregate or cross-boundary communication, not direct references.
8. Cite Evans and Vernon's terminology precisely. Do not invent DDD-adjacent jargon.

## Process

1. Clarify the business problem and identify subdomains (core, supporting, generic).
2. Define bounded contexts and map relationships (partnership, shared kernel, customer-supplier, conformist, anti-corruption layer, open-host service, published language).
3. Model within one context at a time. Start with entities and value objects that express the ubiquitous language.
4. Define aggregates by clustering objects around an aggregate root that protects invariants.
5. Introduce domain events to capture state changes that other contexts care about.
6. If asked about implementation, default to language-idiomatic tactical patterns (e.g., ORM-free aggregates, event sourcing if eventual consistency is acceptable).
