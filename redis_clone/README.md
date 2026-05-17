# Redis Clone

A TCP server that speaks the Redis Serialization Protocol (RESP), providing an in-memory key-value store with TTL support and concurrent client handling via asyncio.

## Supported Commands

| Command | Syntax | Description |
|---------|--------|-------------|
| PING | `PING [message]` | Returns PONG or echoes message |
| ECHO | `ECHO message` | Echoes the message |
| SET | `SET key value [EX seconds] [PX ms]` | Store key-value with optional TTL |
| GET | `GET key` | Retrieve value by key |
| INCR | `INCR key` | Atomically increment integer value |
| DEL | `DEL key [key ...]` | Delete one or more keys |
| EXISTS | `EXISTS key [key ...]` | Check if keys exist |
| EXPIRE | `EXPIRE key seconds [NX]` | Set TTL on existing key |
| TTL | `TTL key` | Get remaining TTL in seconds |
| DBSIZE | `DBSIZE` | Return number of keys |
| FLUSHALL | `FLUSHALL` | Delete all keys |

## Running

```bash
python -m redis.src.server
```

Listens on `127.0.0.1:6380` by default. Configure via `REDIS_HOST` and `REDIS_PORT` environment variables.

## Testing

```bash
# Unit tests (no server needed)
pytest redis/tests/test_resp.py redis/tests/test_store.py

# Integration tests (server must be running)
pytest redis/tests/test_server.py
```
