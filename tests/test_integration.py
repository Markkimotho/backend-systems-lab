import pytest
import asyncio
import aiohttp
import redis.asyncio as aioredis

BASE = 'http://127.0.0.1:8080'  # rate limiter is the front door


@pytest.fixture(autouse=True)
async def flush_state():
    """Start every integration test from clean shared state.

    The rate limiter keys on the real peer IP (127.0.0.1 for localhost) and
    deliberately ignores X-Forwarded-For (spoofable), so tests cannot be
    isolated by faking an IP — they all share the same counters. Flushing the
    clone before each test keeps them independent and order-insensitive.
    """
    c = aioredis.Redis(host='127.0.0.1', port=6380)
    await c.flushall()
    yield
    await c.aclose()


@pytest.mark.asyncio
async def test_full_pipeline():
    """Request travels: Rate Limiter → Load Balancer → Server → Redis."""
    async with aiohttp.ClientSession() as s:
        async with s.get(f'{BASE}/api/data') as resp:
            assert resp.status == 200
            assert 'X-RateLimit-Remaining' in resp.headers
            assert 'X-Served-By' in resp.headers


@pytest.mark.asyncio
async def test_rate_limit_enforced():
    """Requests beyond the /api/data limit (100/60s) must be rejected with 429.

    State is flushed by the autouse fixture, so the sliding window starts empty
    (prev_count = 0) and the burst is sub-second, well inside one 60s window.
    The limiter never allows more than the limit; allowing for the rare case of
    the window ticking mid-burst, we assert it lands at the limit (>=99) and
    every excess request is rejected.
    """
    async with aiohttp.ClientSession() as s:
        responses = []
        for _ in range(105):
            resp = await s.get(f'{BASE}/api/data')
            responses.append(resp.status)
            resp.release()

        ok_count = sum(1 for st in responses if st == 200)
        rejected_count = sum(1 for st in responses if st == 429)
        assert 429 in responses
        assert ok_count <= 100              # limit is never exceeded
        assert ok_count >= 99               # and is reached (boundary tolerance)
        assert ok_count + rejected_count == 105  # every request is 200 or 429


@pytest.mark.asyncio
async def test_session_persistence():
    """Same session cookie always routes to the same backend.

    Uses /health (limit 1000/60s) so the five probe requests can never trip the
    rate limiter and lose their X-Served-By header.
    """
    jar = aiohttp.CookieJar(unsafe=True)  # unsafe=True needed for IP address cookies
    async with aiohttp.ClientSession(cookie_jar=jar) as s:
        servers = set()
        for _ in range(5):
            async with s.get(f'{BASE}/health') as resp:
                assert resp.status == 200
                served_by = resp.headers.get('X-Served-By')
                assert served_by is not None
                servers.add(served_by)
        assert len(servers) == 1  # always the same server
