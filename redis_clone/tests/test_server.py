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


@pytest.mark.asyncio
async def test_get_missing_returns_none(r):
    """GET on a missing key over a default (RESP3) client must return None.

    Regression: the clone used to encode null as the RESP2 `$-1\r\n`, which a
    RESP3 client cannot parse — the read desynced and timed out.
    """
    await r.delete('surely_absent')
    assert await r.get('surely_absent') is None


@pytest.mark.asyncio
async def test_resp3_pipeline_with_null_reply(r):
    """The rate limiter's exact pattern: a MULTI/EXEC pipeline whose first reply
    is a null (GET on a missing key). This is what 500'd the whole HTTP pipeline
    before the protocol-aware null fix.
    """
    await r.delete('pl_prev', 'pl_curr')
    pipe = r.pipeline()  # transaction -> MULTI/EXEC
    pipe.get('pl_prev')        # miss -> null, the failing element
    pipe.incr('pl_curr')       # -> 1
    pipe.expire('pl_curr', 120, nx=True)  # -> True
    results = await pipe.execute()
    assert results[0] is None
    assert results[1] == 1
    assert results[2] is True
    await r.delete('pl_curr')
