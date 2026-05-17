import math
import time
import redis.asyncio as aioredis
from dataclasses import dataclass
from typing import Tuple


@dataclass
class RateLimitConfig:
    limit: int = 100
    window_seconds: int = 60


class RateLimiter:
    def __init__(self, redis_client: aioredis.Redis, config: RateLimitConfig):
        self.redis = redis_client
        self.config = config

    def _base_key(self, ip: str, endpoint: str) -> str:
        path = endpoint.split('?')[0].rstrip('/')
        return f'rl:{ip}:{path}'

    async def is_allowed(self, ip: str, endpoint: str) -> Tuple[bool, int, int, int]:
        """
        Sliding window counter rate limiting (two-bucket approximation).

        Uses the current and previous fixed-window bucket counts to estimate
        the request rate over a rolling window:

            estimated = prev_count × (1 − elapsed_fraction) + curr_count

        This eliminates the fixed-window double-burst problem where a client
        could send 2×limit requests by straddling two window boundaries.

        Returns:
            allowed      — True if the request should proceed
            remaining    — estimated tokens remaining after this request
            retry_after  — seconds until the current window expires (0 if allowed)
            reset_at     — Unix timestamp when the current window expires
        """
        now = time.time()
        window = self.config.window_seconds
        curr_window = math.floor(now / window)
        prev_window = curr_window - 1
        elapsed_fraction = (now % window) / window

        base = self._base_key(ip, endpoint)
        curr_key = f'{base}:{curr_window}'
        prev_key = f'{base}:{prev_window}'

        pipe = self.redis.pipeline()
        pipe.get(prev_key)
        pipe.incr(curr_key)
        pipe.expire(curr_key, window * 2, nx=True)  # keep for 2 windows so prev is readable
        results = await pipe.execute()

        prev_count = int(results[0] or 0)
        curr_count = int(results[1])  # includes this request

        estimated = prev_count * (1.0 - elapsed_fraction) + curr_count

        allowed = estimated <= self.config.limit
        remaining = max(0, int(self.config.limit - estimated))
        reset_at = int((curr_window + 1) * window)
        retry_after = reset_at - int(now) if not allowed else 0

        return allowed, remaining, retry_after, reset_at
