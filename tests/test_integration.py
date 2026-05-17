import pytest
import asyncio
import aiohttp

BASE = 'http://127.0.0.1:8080'  # rate limiter is the front door


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
    """Requests from same IP beyond limit must be rejected with 429."""
    async with aiohttp.ClientSession() as s:
        # Clear any existing counter
        r = aiohttp.ClientSession()
        redis_client = None
        try:
            import redis.asyncio as aioredis
            redis_client = aioredis.Redis(host='127.0.0.1', port=6380)
            await redis_client.delete('rl:10.0.0.1:/api/data')
        finally:
            if redis_client:
                await redis_client.aclose()
            await r.close()

        responses = []
        for _ in range(105):
            resp = await s.get(
                f'{BASE}/api/data',
                headers={'X-Forwarded-For': '10.0.0.1'},
            )
            responses.append(resp.status)
            resp.release()

        assert 429 in responses
        ok_count = sum(1 for s in responses if s == 200)
        rejected_count = sum(1 for s in responses if s == 429)
        assert ok_count == 100
        assert rejected_count == 5


@pytest.mark.asyncio
async def test_session_persistence():
    """Same session cookie always routes to same server."""
    jar = aiohttp.CookieJar(unsafe=True)  # unsafe=True needed for IP address cookies
    async with aiohttp.ClientSession(cookie_jar=jar) as s:
        servers = set()
        for _ in range(5):
            async with s.get(f'{BASE}/api/data') as resp:
                served_by = resp.headers.get('X-Served-By')
                if served_by:
                    servers.add(served_by)
        assert len(servers) == 1  # always same server
