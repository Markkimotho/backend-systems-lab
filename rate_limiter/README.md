# Rate Limiter

An HTTP middleware that throttles requests per-IP and per-endpoint using a token bucket algorithm backed by the Redis clone.

## How It Works

1. Client sends HTTP request to port 8080
2. Rate limiter constructs key `rl:{ip}:{endpoint}` and runs `INCR` + `EXPIRE NX` in Redis
3. If count ≤ limit → forwards request to the load balancer
4. If count > limit → returns `429 Too Many Requests` with `Retry-After` header

## Endpoints & Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/api/search` | 10 req | 60s |
| `/api/data` | 100 req | 60s |
| `/api/upload` | 5 req | 60s |
| `/health` | 1000 req | 60s |
| Default | 60 req | 60s |

## Response Headers

- `X-RateLimit-Limit` — max requests per window
- `X-RateLimit-Remaining` — tokens left
- `Retry-After` — seconds until window resets (on 429)

## Running

```bash
python -m rate_limiter.src.server
```

Listens on port 8080. Configure via environment variables.

## Testing

```bash
pytest rate_limiter/tests/
```
