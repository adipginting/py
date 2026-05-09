# py-coding-agent

A Python coding agent built with Clean Architecture, Test-Driven Development, and Domain-Driven Design.

Port of [pi](https://github.com/earendil-works/pi-mono).

## Development

Requires Python 3.12+ and Poetry.

```bash
poetry install --with dev
poetry run pytest
poetry run ruff check src tests
poetry run mypy src
```
