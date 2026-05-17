# Load Balancer

An async reverse proxy that distributes requests across backend servers using round-robin or least-connections routing, with health checking and Redis-backed session persistence.

## Features

- **Round-robin** and **least-connections** routing algorithms
- **Weighted round-robin** for heterogeneous server capacity
- **Health checking** — periodic pings remove failed servers from the pool
- **Session persistence** — sticky cookie routes same client to same server via Redis
- **Failover** — automatic rerouting when servers fail

## Architecture

```
Request → Session Lookup (Redis) → Health Filter → Pick Algorithm → Proxy to Server
```

## Running

```bash
python -m load_balancer.src.server
```

Listens on port 8090. Configure via environment variables.

## Testing

```bash
pytest load_balancer/tests/
```
