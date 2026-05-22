"""EnvAuthResolver adapter: read secrets from environment variables."""

from __future__ import annotations

import os


class EnvAuthResolver:
    """Resolve authentication secrets from the process environment."""

    async def resolve(self, key: str) -> str:
        """Return the value of the environment variable named *key*.

        Raises:
            KeyError: If the environment variable is not set.
        """
        try:
            return os.environ[key]
        except KeyError as exc:
            raise KeyError(f"Secret not found in environment: {key}") from exc
