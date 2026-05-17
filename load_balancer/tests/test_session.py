import pytest
import redis.asyncio as aioredis
from load_balancer.src.session import SessionRouter


@pytest.fixture
async def redis_client():
    r = aioredis.Redis(host='127.0.0.1', port=6380)
    yield r
    await r.aclose()


@pytest.fixture
async def router(redis_client):
    return SessionRouter(redis_client, ttl=60)


@pytest.mark.asyncio
async def test_pin_and_get_session(router):
    await router.pin_session('abc123', 'http://127.0.0.1:8001')
    result = await router.get_server('abc123')
    assert result == 'http://127.0.0.1:8001'
    await router.clear_session('abc123')


@pytest.mark.asyncio
async def test_get_missing_session(router):
    result = await router.get_server('nonexistent')
    assert result is None


@pytest.mark.asyncio
async def test_clear_session(router):
    await router.pin_session('del_me', 'http://127.0.0.1:8002')
    await router.clear_session('del_me')
    result = await router.get_server('del_me')
    assert result is None


@pytest.mark.asyncio
async def test_overwrite_session(router):
    await router.pin_session('sess1', 'http://127.0.0.1:8001')
    await router.pin_session('sess1', 'http://127.0.0.1:8002')
    result = await router.get_server('sess1')
    assert result == 'http://127.0.0.1:8002'
    await router.clear_session('sess1')
