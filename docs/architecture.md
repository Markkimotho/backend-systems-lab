# Architecture

## System Overview

Backend Systems Lab is a distributed backend system with three interconnected components:

![System Architecture](diagrams/system-architecture.png)

## Request Flow

![Request Flow — Sequence Diagram](diagrams/request-flow-sequence.png)

## Component Internal Flows

![Component Internal Flows](diagrams/component-flows.png)

## Data Flow

1. **Client** sends HTTP request to the Rate Limiter (port 8080)
2. **Rate Limiter** queries Redis for `rl:{ip}:{endpoint}` counter
   - Under limit → INCR counter, set TTL (EXPIRE NX), forward to Load Balancer
   - Over limit → return 429 with Retry-After header
3. **Load Balancer** checks Redis for session cookie → sticky routing
   - No session → pick server via round-robin, pin session in Redis
   - Session exists but server unhealthy → clear session, re-route
4. **Backend Server** processes request, may read/write Redis cache
5. Response flows back through the pipeline with rate limit and routing headers

## Component Interaction

- All components share state through the Redis clone
- Rate limit counters use `INCR` + `EXPIRE NX` for atomic window-based counting
- Session persistence uses `SET` with TTL for automatic cleanup
- Health checker runs periodic background checks, removing failed servers from the pool

## Key Design Decisions

- **Lazy TTL eviction** in Redis clone — entries are checked on read, not via background thread
- **EXPIRE NX** for rate limiting — TTL is set only once per window, preventing reset on every request
- **asyncio throughout** — all I/O is non-blocking for maximum concurrency
- **No external dependencies** for core logic — only standard library + aiohttp for HTTP
