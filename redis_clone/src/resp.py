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


def encode_resp(value: Any) -> bytes:
    """
    Encode a Python value back into RESP bytes.
    Rules:
      None   → null bulk string ($-1\r\n)
      str    → simple string (+value\r\n)
      int    → integer (:value\r\n)
      bytes  → bulk string ($len\r\nbytes\r\n)
      list   → array (*len\r\n + encode each element)
      Exception → error (-message\r\n)
    """
    if value is None:
        return b'$-1\r\n'
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
            parts.append(encode_resp(item))
        return b''.join(parts)
    raise TypeError(f'Cannot encode type {type(value).__name__}')
