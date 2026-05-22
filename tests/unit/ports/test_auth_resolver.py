"""Tests for AuthResolver port."""

from __future__ import annotations

import pytest


class FakeAuthResolver:
    """Hand-written fake for AuthResolver."""

    def __init__(self, secrets: dict[str, str] | None = None) -> None:
        self._secrets = secrets or {}
        self.calls: list[str] = []

    async def resolve(self, key: str) -> str:
        self.calls.append(key)
        if key not in self._secrets:
            raise KeyError(f"Secret not found: {key}")
        return self._secrets[key]


@pytest.mark.anyio
async def test_auth_resolver_returns_secret() -> None:
    """A resolver returns the secret matching the requested key."""
    resolver = FakeAuthResolver({"OPENAI_API_KEY": "sk-test"})

    result = await resolver.resolve("OPENAI_API_KEY")

    assert result == "sk-test"
    assert resolver.calls == ["OPENAI_API_KEY"]


@pytest.mark.anyio
async def test_auth_resolver_raises_for_missing_key() -> None:
    """A resolver raises when the requested key is absent."""
    resolver = FakeAuthResolver()

    with pytest.raises(KeyError):
        await resolver.resolve("MISSING_KEY")
