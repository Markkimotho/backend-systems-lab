import pytest
import asyncio
import io
from redis_clone.src.resp import parse_resp, encode_resp


class FakeStreamReader:
    """Wraps bytes into an asyncio.StreamReader-like interface for testing."""

    def __init__(self, data: bytes):
        self._reader = asyncio.StreamReader()
        self._reader.feed_data(data)
        self._reader.feed_eof()

    async def readline(self):
        return await self._reader.readline()

    async def readexactly(self, n):
        return await self._reader.readexactly(n)


# --- parse_resp tests ---

@pytest.mark.asyncio
async def test_parse_simple_string():
    reader = FakeStreamReader(b'+OK\r\n')
    result = await parse_resp(reader)
    assert result == 'OK'


@pytest.mark.asyncio
async def test_parse_integer():
    reader = FakeStreamReader(b':42\r\n')
    result = await parse_resp(reader)
    assert result == 42


@pytest.mark.asyncio
async def test_parse_bulk_string():
    reader = FakeStreamReader(b'$5\r\nhello\r\n')
    result = await parse_resp(reader)
    assert result == 'hello'


@pytest.mark.asyncio
async def test_parse_null_bulk_string():
    reader = FakeStreamReader(b'$-1\r\n')
    result = await parse_resp(reader)
    assert result is None


@pytest.mark.asyncio
async def test_parse_array():
    reader = FakeStreamReader(b'*2\r\n$3\r\nGET\r\n$3\r\nfoo\r\n')
    result = await parse_resp(reader)
    assert result == ['GET', 'foo']


@pytest.mark.asyncio
async def test_parse_ping_command():
    reader = FakeStreamReader(b'*1\r\n$4\r\nPING\r\n')
    result = await parse_resp(reader)
    assert result == ['PING']


@pytest.mark.asyncio
async def test_parse_error():
    reader = FakeStreamReader(b'-ERR unknown command\r\n')
    with pytest.raises(Exception, match='ERR unknown command'):
        await parse_resp(reader)


@pytest.mark.asyncio
async def test_parse_empty_stream():
    reader = FakeStreamReader(b'')
    with pytest.raises(asyncio.IncompleteReadError):
        await parse_resp(reader)


# --- encode_resp tests ---

def test_encode_none():
    assert encode_resp(None) == b'$-1\r\n'


def test_encode_string():
    assert encode_resp('OK') == b'+OK\r\n'


def test_encode_integer():
    assert encode_resp(42) == b':42\r\n'


def test_encode_bytes():
    assert encode_resp(b'hello') == b'$5\r\nhello\r\n'


def test_encode_list():
    result = encode_resp(['OK', 42])
    assert result == b'*2\r\n+OK\r\n:42\r\n'


def test_encode_exception():
    result = encode_resp(Exception('bad'))
    assert result == b'-ERR bad\r\n'


def test_encode_bool():
    assert encode_resp(True) == b':1\r\n'
    assert encode_resp(False) == b':0\r\n'


def test_encode_nested_list():
    result = encode_resp([['a', 'b'], 1])
    assert result == b'*2\r\n*2\r\n+a\r\n+b\r\n:1\r\n'


def test_encode_unsupported_type():
    with pytest.raises(TypeError):
        encode_resp(3.14)
