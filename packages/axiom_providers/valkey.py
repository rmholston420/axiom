"""Valkey/Redis adapter — async thin wrapper."""
from __future__ import annotations

import redis.asyncio as aioredis
from axiom_core.settings import settings


class ValkeyProvider:
    """Async client for the Valkey/Redis instance."""

    def __init__(self) -> None:
        self._client: aioredis.Redis = aioredis.from_url(
            settings.axiom_redis_url,
            decode_responses=True,
        )

    @property
    def client(self) -> aioredis.Redis:
        return self._client

    async def ping(self) -> bool:
        """Return True if Valkey is reachable."""
        try:
            return await self._client.ping()  # type: ignore[return-value]
        except Exception:  # noqa: BLE001
            return False

    async def aclose(self) -> None:
        await self._client.aclose()
