---
name: tdd
description: Enforces strict test-driven development workflow. Use when the user wants to write code via TDD, review TDD discipline, or refactor using tests as the primary design tool.
---

# Test-Driven Development (TDD)

Guide the user through the red-green-refactor cycle with strict discipline.

## Rules

1. Never write production code without a failing test first. No exceptions.
2. Write the smallest possible test that fails. One concept per test.
3. Write the smallest possible production code to make the test pass. No premature abstractions.
4. Refactor only on green. Never refactor while tests are red.
5. All refactorings must preserve passing tests.
6. Tests are first-class design documentation. Name them to describe behavior, not methods.
7. If the user asks for production code before a test, refuse and ask what behavior they want to pin down.
8. If existing tests are not passing, halt and fix them before adding new behavior.
9. When writing tests, think about the desired API from the caller's perspective (outside-in). The test is the first client of the code.
10. After green, aggressively refactor: remove duplication, improve names, clarify intent.

## Workflow

For each new behavior:

1. **Red** — Write a failing test. State the test name and expected outcome.
2. **Green** — Implement the minimal code to pass. No design purity yet.
3. **Refactor** — Clean up duplication and names while tests stay green.
4. Ask the user if they want to proceed to the next behavior.

## Red Flags to Call Out

- Writing a test that cannot fail (false confidence).
- Multiple assertions masking a single concept.
- Tests tightly coupled to implementation details (e.g., private method names).
- Production code written without any test coverage.
- Refactoring on red.
