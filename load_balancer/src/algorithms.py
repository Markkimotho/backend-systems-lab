from .pool import BackendServer


class RoundRobin:
    """Cycles through healthy servers in order."""

    def __init__(self):
        self._index = 0

    def pick(self, servers: list[BackendServer]) -> BackendServer:
        healthy = [s for s in servers if s.is_healthy]
        if not healthy:
            raise RuntimeError('No healthy servers in pool')
        server = healthy[self._index % len(healthy)]
        self._index = (self._index + 1) % max(1, len(healthy))
        return server


class LeastConnections:
    """Routes to the server with fewest active connections."""

    def pick(self, servers: list[BackendServer]) -> BackendServer:
        healthy = [s for s in servers if s.is_healthy]
        if not healthy:
            raise RuntimeError('No healthy servers in pool')
        return min(healthy, key=lambda s: s.active_connections)


class WeightedRoundRobin:
    """Servers with higher weight get proportionally more requests."""

    def __init__(self):
        self._counters: dict[str, int] = {}

    def pick(self, servers: list[BackendServer]) -> BackendServer:
        healthy = [s for s in servers if s.is_healthy]
        if not healthy:
            raise RuntimeError('No healthy servers in pool')
        weighted = [s for s in healthy for _ in range(s.weight)]
        total = sum(s.weight for s in healthy)
        idx = sum(self._counters.values()) % total
        server = weighted[idx]
        self._counters[server.address] = self._counters.get(server.address, 0) + 1
        return server
