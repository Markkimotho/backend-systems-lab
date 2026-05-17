# API Reference

## Redis Clone (TCP :6380)

Speaks the Redis Serialization Protocol (RESP). Compatible with standard Redis clients.

### Commands

| Command | Syntax | Response | Description |
|---------|--------|----------|-------------|
| `PING` | `PING [message]` | `+PONG\r\n` | Connection test |
| `ECHO` | `ECHO message` | `+message\r\n` | Echo message back |
| `SET` | `SET key value [EX s] [PX ms]` | `+OK\r\n` | Store key with optional TTL |
| `GET` | `GET key` | Bulk string or null | Retrieve value |
| `INCR` | `INCR key` | Integer | Atomic increment (creates key at 0 if missing) |
| `DEL` | `DEL key [key ...]` | Integer (count) | Delete keys |
| `EXISTS` | `EXISTS key [key ...]` | Integer (count) | Check key existence |
| `EXPIRE` | `EXPIRE key seconds [NX]` | Integer (0/1) | Set TTL; NX = only if no TTL |
| `TTL` | `TTL key` | Integer | Remaining TTL (-1 = none, -2 = missing) |
| `DBSIZE` | `DBSIZE` | Integer | Number of keys |
| `FLUSHALL` | `FLUSHALL` | `+OK\r\n` | Delete all keys |

---

## Rate Limiter (HTTP :8080)

Transparent HTTP proxy. All paths are forwarded to the Load Balancer after rate check.

### Request Flow

Any HTTP method to any path is accepted. Rate limiting is based on:
- `X-Forwarded-For` header (or `request.remote` as fallback) for IP extraction
- Request path for per-endpoint limits

### Response Headers (all responses)

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Maximum requests per window |
| `X-RateLimit-Remaining` | Requests remaining in current window |

### Response Headers (429 only)

| Header | Description |
|--------|-------------|
| `Retry-After` | Seconds until rate limit window resets |
| `X-RateLimit-Reset` | Same as Retry-After |

### Status Codes

| Code | Meaning |
|------|---------|
| 200 | Request forwarded and response returned |
| 429 | Rate limit exceeded |
| 502 | Load balancer unreachable |

---

## Load Balancer (HTTP :8090)

Reverse proxy distributing requests across backend servers.

### Response Headers

| Header | Description |
|--------|-------------|
| `X-Served-By` | Address of the server that handled the request |
| `Set-Cookie: session_id=...` | Session cookie for sticky routing |

### Status Codes

| Code | Meaning |
|------|---------|
| 200 | Request proxied successfully |
| 502 | Selected backend server unreachable |
| 503 | No healthy servers available |

### Session Persistence

The load balancer sets a `session_id` cookie on the first request. Subsequent requests with that cookie route to the same server. If the pinned server becomes unhealthy, the session is cleared and a new server is assigned.

---

## Backend Servers (HTTP :8001-8003)

Mock servers for demonstration.

### Endpoints

| Path | Method | Response |
|------|--------|----------|
| `/health` | GET | `200 OK` |
| `/*` | Any | JSON `{"server": "server-{port}", "path": "...", "method": "..."}` |
