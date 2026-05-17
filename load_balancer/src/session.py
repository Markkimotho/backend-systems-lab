import redis.asyncio as aioredis
from typing import Optional


class SessionRouter:
    """
    Stores client session → server mapping in Redis.
    When a client sends a session_id cookie, they always route to the same server.
    When that server goes unhealthy, the session is cleared and they get re-routed.
    """

    def __init__(self, redis_client: aioredis.Redis, ttl: int = 3600):
        self.redis = redis_client
        self.ttl = ttl

    def _key(self, session_id: str) -> str:
        return f'session:{session_id}'

    async def get_server(self, session_id: str) -> Optional[str]:
        val = await self.redis.get(self._key(session_id))
        return val.decode() if val else None

    async def pin_session(self, session_id: str, server_address: str) -> None:
        await self.redis.set(self._key(session_id), server_address, ex=self.ttl)

    async def clear_session(self, session_id: str) -> None:
        await self.redis.delete(self._key(session_id))
