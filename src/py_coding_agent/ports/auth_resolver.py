"""AuthResolver port: resolve API keys and credentials."""

from __future__ import annotations

from typing import Protocol


class AuthResolver(Protocol):
    """Outbound port for resolving authentication secrets.

    Implementations may read from environment variables,
    encrypted stores, OAuth token caches, or user prompts.
    """

    async def resolve(self, key: str) -> str:
        """Return the secret associated with the given key.

        Args:
            key: A provider-specific identifier (e.g. "OPENAI_API_KEY").

        Returns:
            The resolved secret string.

        Raises:
            KeyError: If the secret cannot be found.
        """
        ...
