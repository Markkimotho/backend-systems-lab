import asyncio
from typing import Any


async def parse_resp(reader: asyncio.StreamReader) -> Any:
    """
    Read one RESP value from the stream.
    Prefix byte determines type:
      +  Simple string  → return str
      -  Error          → raise Exception
      :  Integer        → return int
      $  Bulk string    → return str or None (null bulk = $-1)
      *  Array          → return list (recurse for each element)
    """
    line = await reader.readline()
    if not line:
        raise asyncio.IncompleteReadError(b'', 0)

    prefix = chr(line[0])
    data = line[1:].rstrip(b'\r\n').decode('utf-8', errors='replace')

    if prefix == '+':
        return data
    elif prefix == '-':
        raise Exception(data)
    elif prefix == ':':
        return int(data)
    elif prefix == '$':
        n = int(data)
        if n == -1:
            return None
        bulk = await reader.readexactly(n + 2)  # +2 eats the trailing \r\n
        return bulk[:-2].decode('utf-8')
    elif prefix == '*':
        count = int(data)
        if count == -1:
            return None
        return [await parse_resp(reader) for _ in range(count)]
    else:
        raise ValueError(f'Unknown RESP prefix: {prefix!r}')


def encode_resp(value: Any, proto: int = 2) -> bytes:
    """
    Encode a Python value back into RESP bytes for the given protocol version.

    Every type the clone emits is byte-identical between RESP2 and RESP3 except
    null: RESP3 dropped the `$-1` / `*-1` forms and uses a dedicated null type
    `_\r\n`. A RESP3 client (redis-py defaults to RESP3 since v5) cannot parse
    `$-1` and will desync, so null must follow the negotiated protocol.

    Rules:
      None   → null  (RESP3: _\r\n   RESP2: $-1\r\n)
      str    → simple string (+value\r\n)
      int    → integer (:value\r\n)
      bytes  → bulk string ($len\r\nbytes\r\n)
      list   → array (*len\r\n + encode each element)
      Exception → error (-message\r\n)
    """
    if value is None:
        return b'_\r\n' if proto == 3 else b'$-1\r\n'
    if isinstance(value, Exception):
        return f'-ERR {value}\r\n'.encode()
    if isinstance(value, bool):
        return f':{int(value)}\r\n'.encode()
    if isinstance(value, int):
        return f':{value}\r\n'.encode()
    if isinstance(value, str):
        return f'+{value}\r\n'.encode()
    if isinstance(value, bytes):
        return f'${len(value)}\r\n'.encode() + value + b'\r\n'
    if isinstance(value, list):
        parts = [f'*{len(value)}\r\n'.encode()]
        for item in value:
            parts.append(encode_resp(item, proto))
        return b''.join(parts)
    raise TypeError(f'Cannot encode type {type(value).__name__}')


def encode_hello(proto: int) -> bytes:
    """
    Build a HELLO reply for protocol negotiation.

    redis-py defaults to RESP3 since v5 (DEFAULT_RESP_VERSION = 3) and redis-cli
    sends HELLO with `-3`; both issue HELLO on connect. The clone only ever emits
    RESP2 frames, which are a strict subset the RESP3 parser also accepts, so we
    answer HELLO and report whichever protocol the client requested.

      proto == 3 → RESP3 map (%N) so a client's .get('proto') lookup works.
      proto == 2 → RESP2 flat array (*N) of alternating key/value.
    """
    fields = [
        ('server', 'redis-clone'),
        ('version', '1.0.0'),
        ('proto', proto),
        ('id', 1),
        ('mode', 'standalone'),
        ('role', 'master'),
        ('modules', []),
    ]
    if proto == 3:
        parts = [f'%{len(fields)}\r\n'.encode()]
        for key, val in fields:
            parts.append(f'${len(key)}\r\n{key}\r\n'.encode())
            parts.append(encode_resp(val))
        return b''.join(parts)
    flat: list = []
    for key, val in fields:
        flat.extend((key, val))
    return encode_resp(flat)
