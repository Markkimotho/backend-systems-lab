import pytest
from load_balancer.src.pool import BackendServer, ServerStatus
from load_balancer.src.algorithms import RoundRobin, LeastConnections, WeightedRoundRobin


def make_servers():
    return [
        BackendServer(host='127.0.0.1', port=8001),
        BackendServer(host='127.0.0.1', port=8002),
        BackendServer(host='127.0.0.1', port=8003),
    ]


class TestRoundRobin:
    def test_cycles_through_servers(self):
        servers = make_servers()
        rr = RoundRobin()
        picked = [rr.pick(servers).port for _ in range(6)]
        assert picked == [8001, 8002, 8003, 8001, 8002, 8003]

    def test_skips_unhealthy(self):
        servers = make_servers()
        servers[1].status = ServerStatus.UNHEALTHY
        rr = RoundRobin()
        picked = [rr.pick(servers).port for _ in range(4)]
        assert 8002 not in picked

    def test_raises_when_all_unhealthy(self):
        servers = make_servers()
        for s in servers:
            s.status = ServerStatus.UNHEALTHY
        rr = RoundRobin()
        with pytest.raises(RuntimeError, match='No healthy servers'):
            rr.pick(servers)


class TestLeastConnections:
    def test_picks_least_loaded(self):
        servers = make_servers()
        servers[0].active_connections = 5
        servers[1].active_connections = 2
        servers[2].active_connections = 8
        lc = LeastConnections()
        assert lc.pick(servers).port == 8002

    def test_skips_unhealthy(self):
        servers = make_servers()
        servers[1].active_connections = 0  # lowest
        servers[1].status = ServerStatus.UNHEALTHY
        servers[0].active_connections = 3
        servers[2].active_connections = 5
        lc = LeastConnections()
        assert lc.pick(servers).port == 8001


class TestWeightedRoundRobin:
    def test_weighted_distribution(self):
        servers = [
            BackendServer(host='127.0.0.1', port=8001, weight=2),
            BackendServer(host='127.0.0.1', port=8002, weight=1),
        ]
        wrr = WeightedRoundRobin()
        counts = {8001: 0, 8002: 0}
        for _ in range(30):
            s = wrr.pick(servers)
            counts[s.port] += 1
        # Server with weight 2 should get roughly 2x the requests
        assert counts[8001] > counts[8002]
