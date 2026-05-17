import pytest
import asyncio
import redis.asyncio as aioredis


@pytest.fixture
async def r():
    client = aioredis.Redis(host='127.0.0.1', port=6380)
    yield client
    await client.aclose()


@pytest.mark.asyncio
async def test_ping(r):
    assert await r.ping()


@pytest.mark.asyncio
async def test_set_get_roundtrip(r):
    await r.set('hello', 'world')
    assert await r.get('hello') == b'world'
    await r.delete('hello')


@pytest.mark.asyncio
async def test_set_with_expiry(r):
    await r.set('tmp', 'val', ex=1)
    assert await r.get('tmp') == b'val'
    await asyncio.sleep(1.1)
    assert await r.get('tmp') is None


@pytest.mark.asyncio
async def test_incr(r):
    await r.delete('test_counter')
    assert await r.incr('test_counter') == 1
    assert await r.incr('test_counter') == 2
    await r.delete('test_counter')


@pytest.mark.asyncio
async def test_del(r):
    await r.set('del_key', 'val')
    result = await r.delete('del_key')
    assert result == 1
    assert await r.get('del_key') is None


@pytest.mark.asyncio
async def test_exists(r):
    await r.set('ex_key', 'val')
    assert await r.exists('ex_key') == 1
    assert await r.exists('no_key') == 0
    await r.delete('ex_key')


@pytest.mark.asyncio
async def test_concurrent_incr(r):
    """100 concurrent INCRs on same key must produce exactly 100."""
    key = 'concurrent_test_key'
    await r.delete(key)
    await asyncio.gather(*[r.incr(key) for _ in range(100)])
    assert int(await r.get(key)) == 100
    await r.delete(key)
