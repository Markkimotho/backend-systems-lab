import asyncio
import redis.asyncio as aioredis


async def get_redis(port: int = 6380) -> aioredis.Redis:
    return aioredis.Redis(host='127.0.0.1', port=port)
