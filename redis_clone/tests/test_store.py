import pytest
import time
from redis_clone.src.store import Store


def test_set_get():
    s = Store()
    s.set('foo', 'bar')
    assert s.get('foo') == 'bar'


def test_get_missing():
    assert Store().get('missing') is None


def test_overwrite():
    s = Store()
    s.set('key', 'v1')
    s.set('key', 'v2')
    assert s.get('key') == 'v2'


# ── LRU eviction tests ────────────────────────────────────────────────────────

def test_lru_evicts_when_over_limit():
    s = Store(max_keys=2)
    s.set('a', '1')
    s.set('b', '2')
    s.set('c', '3')        # should evict 'a' (LRU)
    assert s.get('a') is None
    assert s.get('b') == '2'
    assert s.get('c') == '3'


def test_lru_access_order_updates():
    s = Store(max_keys=2)
    s.set('a', '1')
    s.set('b', '2')
    s.get('a')             # 'a' is now most recently used
    s.set('c', '3')        # should evict 'b' (LRU), not 'a'
    assert s.get('a') == '1'
    assert s.get('b') is None
    assert s.get('c') == '3'


def test_lru_zero_means_unlimited():
    s = Store(max_keys=0)
    for i in range(1000):
        s.set(f'key{i}', str(i))
    assert s.dbsize() == 1000


def test_expiry():
    s = Store()
    s.set('tmp', 'val', ex=1)
    assert s.get('tmp') == 'val'
    time.sleep(1.1)
    assert s.get('tmp') is None


def test_px_expiry():
    s = Store()
    s.set('tmp', 'val', px=500)
    assert s.get('tmp') == 'val'
    time.sleep(0.6)
    assert s.get('tmp') is None


def test_incr_creates_key():
    s = Store()
    assert s.incr('counter') == 1
    assert s.incr('counter') == 2


def test_incr_existing_key():
    s = Store()
    s.set('n', '10')
    assert s.incr('n') == 11


def test_incr_preserves_ttl():
    s = Store()
    s.set('c', '5', ex=60)
    s.incr('c')
    assert s.ttl('c') > 50  # TTL still set


def test_incr_non_integer():
    s = Store()
    s.set('s', 'hello')
    with pytest.raises(ValueError):
        s.incr('s')


def test_delete():
    s = Store()
    s.set('a', '1')
    s.set('b', '2')
    assert s.delete('a', 'b', 'c') == 2  # 'c' doesn't exist


def test_delete_missing():
    s = Store()
    assert s.delete('nonexistent') == 0


def test_exists():
    s = Store()
    s.set('x', '1')
    assert s.exists('x') == 1
    assert s.exists('x', 'missing') == 1


def test_exists_expired():
    s = Store()
    s.set('e', '1', ex=1)
    time.sleep(1.1)
    assert s.exists('e') == 0


def test_expire():
    s = Store()
    s.set('k', 'v')
    assert s.expire('k', 10) == 1
    assert s.ttl('k') > 0


def test_expire_nx():
    s = Store()
    s.set('k', 'v', ex=60)
    # NX should NOT overwrite existing expiry
    assert s.expire('k', 10, nx=True) == 0
    assert s.ttl('k') > 10


def test_expire_nx_on_persistent_key():
    s = Store()
    s.set('k', 'v')  # no expiry
    assert s.expire('k', 10, nx=True) == 1
    assert s.ttl('k') > 0


def test_expire_missing_key():
    s = Store()
    assert s.expire('missing', 10) == 0


def test_ttl_no_expiry():
    s = Store()
    s.set('k', 'v')
    assert s.ttl('k') == -1


def test_ttl_missing_key():
    s = Store()
    assert s.ttl('missing') == -2


def test_dbsize():
    s = Store()
    s.set('a', '1')
    s.set('b', '2')
    assert s.dbsize() == 2


def test_dbsize_expired():
    s = Store()
    s.set('a', '1', ex=1)
    s.set('b', '2')
    time.sleep(1.1)
    assert s.dbsize() == 1


def test_flush():
    s = Store()
    s.set('a', '1')
    s.set('b', '2')
    s.flush()
    assert s.dbsize() == 0
