import math
import time
import pytest
import redis.asyncio as aioredis
from rate_limiter.src.limiter import RateLimiter, RateLimitConfig


@pytest.fixture
async def redis_client():
    r = aioredis.Redis(host='127.0.0.1', port=6380)
    yield r
    await r.aclose()


def _curr_key(ip: str, endpoint: str, window_seconds: int) -> str:
    """Compute the current sliding-window bucket key for cleanup in tests."""
    path = endpoint.split('?')[0].rstrip('/')
    curr_window = math.floor(time.time() / window_seconds)
    return f'rl:{ip}:{path}:{curr_window}'


@pytest.mark.asyncio
async def test_allows_under_limit(redis_client):
    limiter = RateLimiter(redis_client, RateLimitConfig(limit=5, window_seconds=10))
    await redis_client.delete(_curr_key('1.1.1.1', '/test', 10))
    for _ in range(5):
        allowed, _, _, _ = await limiter.is_allowed('1.1.1.1', '/test')
        assert allowed


@pytest.mark.asyncio
async def test_blocks_over_limit(redis_client):
    limiter = RateLimiter(redis_client, RateLimitConfig(limit=3, window_seconds=10))
    await redis_client.delete(_curr_key('2.2.2.2', '/test', 10))
    for _ in range(3):
        await limiter.is_allowed('2.2.2.2', '/test')
    allowed, remaining, retry_after, reset_at = await limiter.is_allowed('2.2.2.2', '/test')
    assert not allowed
    assert remaining == 0
    assert retry_after > 0
    assert reset_at > int(time.time())


@pytest.mark.asyncio
async def test_different_ips_independent(redis_client):
    limiter = RateLimiter(redis_client, RateLimitConfig(limit=1, window_seconds=10))
    await redis_client.delete(_curr_key('3.3.3.3', '/test', 10))
    await redis_client.delete(_curr_key('4.4.4.4', '/test', 10))
    await limiter.is_allowed('3.3.3.3', '/test')
    await limiter.is_allowed('3.3.3.3', '/test')  # 3.3.3.3 is now blocked
    allowed, _, _, _ = await limiter.is_allowed('4.4.4.4', '/test')
    assert allowed  # 4.4.4.4 unaffected


@pytest.mark.asyncio
async def test_remaining_counter_accuracy(redis_client):
    limiter = RateLimiter(redis_client, RateLimitConfig(limit=5, window_seconds=10))
    await redis_client.delete(_curr_key('6.6.6.6', '/test', 10))
    allowed, remaining, _, _ = await limiter.is_allowed('6.6.6.6', '/test')
    assert allowed
    assert remaining == 4
    allowed, remaining, _, _ = await limiter.is_allowed('6.6.6.6', '/test')
    assert remaining == 3


@pytest.mark.asyncio
async def test_counter_continues_after_reject(redis_client):
    """Counter increments even on rejected requests — this is correct INCR behaviour."""
    limiter = RateLimiter(redis_client, RateLimitConfig(limit=2, window_seconds=60))
    curr_key = _curr_key('5.5.5.5', '/test', 60)
    await redis_client.delete(curr_key)
    await limiter.is_allowed('5.5.5.5', '/test')
    await limiter.is_allowed('5.5.5.5', '/test')
    await limiter.is_allowed('5.5.5.5', '/test')  # rejected — count = 3
    await limiter.is_allowed('5.5.5.5', '/test')  # rejected — count = 4
    count = int(await redis_client.get(curr_key))
    assert count == 4
    _, remaining, _, _ = await limiter.is_allowed('5.5.5.5', '/test')
    assert remaining == 0
