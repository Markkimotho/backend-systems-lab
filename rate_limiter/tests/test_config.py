import pytest
import aiohttp
from rate_limiter.src.config import get_config, ENDPOINT_LIMITS


def test_get_known_endpoint():
    config = get_config('/api/search')
    assert config.limit == 10


def test_get_default_endpoint():
    config = get_config('/unknown/path')
    assert config.limit == 60  # default


def test_strips_query_params():
    config = get_config('/api/search?q=hello')
    assert config.limit == 10


def test_strips_trailing_slash():
    config = get_config('/api/data/')
    assert config.limit == 100
