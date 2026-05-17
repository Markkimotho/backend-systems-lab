import pytest
from load_balancer.src.pool import BackendServer, ServerStatus


def make_server(port: int, **kwargs) -> BackendServer:
    return BackendServer(host='127.0.0.1', port=port, **kwargs)


def test_server_address():
    s = make_server(8001)
    assert s.address == 'http://127.0.0.1:8001'


def test_initially_healthy():
    s = make_server(8001)
    assert s.is_healthy


def test_mark_failure_below_threshold():
    s = make_server(8001)
    s.mark_failure(threshold=3)
    assert s.is_healthy  # only 1 failure, need 3


def test_mark_failure_at_threshold():
    s = make_server(8001)
    for _ in range(3):
        s.mark_failure(threshold=3)
    assert not s.is_healthy
    assert s.status == ServerStatus.UNHEALTHY


def test_mark_success_resets():
    s = make_server(8001)
    for _ in range(3):
        s.mark_failure(threshold=3)
    assert not s.is_healthy
    s.mark_success()
    assert s.is_healthy
    assert s.consecutive_failures == 0


def test_draining_status():
    s = make_server(8001)
    s.status = ServerStatus.DRAINING
    assert not s.is_healthy
