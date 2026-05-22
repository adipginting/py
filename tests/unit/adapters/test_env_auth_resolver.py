"""Tests for EnvAuthResolver adapter."""

from __future__ import annotations

import pytest

from py_coding_agent.adapters.env_auth_resolver import EnvAuthResolver


@pytest.mark.anyio
async def test_env_auth_resolver_returns_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    """EnvAuthResolver reads a secret from an environment variable."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    resolver = EnvAuthResolver()

    result = await resolver.resolve("OPENAI_API_KEY")

    assert result == "sk-test"


@pytest.mark.anyio
async def test_env_auth_resolver_raises_for_missing_variable() -> None:
    """EnvAuthResolver raises KeyError when the variable is absent."""
    resolver = EnvAuthResolver()

    with pytest.raises(KeyError, match="OPENAI_API_KEY"):
        await resolver.resolve("OPENAI_API_KEY")
