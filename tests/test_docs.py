"""Anti-drift gate test for the documentation site.

Documentation rots when code changes and prose doesn't. These checks pull the
ground truth out of the source (the command dispatcher, the rate-limit config)
and assert the integration guide still states it. Deterministic, no network,
runs in the free gate lane. If you add a Redis command or change a limit, this
fails until docs/index.md is updated to match.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = (ROOT / 'docs' / 'index.md').read_text()


def test_every_dispatched_command_is_documented():
    """Each command handled by the clone's dispatcher must appear in the guide."""
    commands_src = (ROOT / 'redis_clone' / 'src' / 'commands.py').read_text()
    dispatched = set(re.findall(r"name == '([A-Z]+)'", commands_src))
    # sanity: the dispatcher really did define commands
    assert {'GET', 'SET', 'INCR'} <= dispatched
    missing = sorted(c for c in dispatched if c not in DOCS)
    assert not missing, f'commands missing from docs/index.md: {missing}'


def test_connection_commands_documented():
    """HELLO/AUTH/MULTI live in the server loop, not dispatch — document them too."""
    for cmd in ('HELLO', 'AUTH', 'MULTI', 'EXEC', 'DISCARD'):
        assert cmd in DOCS, f'{cmd} not documented'


def test_endpoint_limits_match_config():
    """Every per-endpoint limit in config.py must be shown with its number."""
    config_src = (ROOT / 'rate_limiter' / 'src' / 'config.py').read_text()
    pairs = re.findall(r"'(/[^']+)':\s*RateLimitConfig\(limit=(\d+)", config_src)
    assert pairs, 'could not parse ENDPOINT_LIMITS from config.py'
    for path, limit in pairs:
        assert path in DOCS, f'endpoint {path} not documented'
        assert limit in DOCS, f'limit {limit} for {path} not documented'


def test_default_limit_documented():
    config_src = (ROOT / 'rate_limiter' / 'src' / 'config.py').read_text()
    m = re.search(r'DEFAULT_CONFIG\s*=\s*RateLimitConfig\(limit=(\d+)', config_src)
    assert m, 'could not parse DEFAULT_CONFIG'
    assert m.group(1) in DOCS, 'default rate limit not documented'


def test_service_ports_documented():
    """The four service ports the reader needs must be present."""
    for port in ('6380', '8080', '8090', '8001'):
        assert port in DOCS, f'port {port} not documented'


def test_unsupported_types_are_called_out():
    """The guide must warn about the missing data types (the #1 integration trap)."""
    for term in ('hashes', 'SCAN', 'pub/sub'):
        assert term in DOCS, f'limitation "{term}" not documented'
