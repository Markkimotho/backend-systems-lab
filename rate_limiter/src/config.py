from .limiter import RateLimitConfig

ENDPOINT_LIMITS: dict[str, RateLimitConfig] = {
    '/api/search':  RateLimitConfig(limit=10,   window_seconds=60),
    '/api/data':    RateLimitConfig(limit=100,  window_seconds=60),
    '/api/upload':  RateLimitConfig(limit=5,    window_seconds=60),
    '/health':      RateLimitConfig(limit=1000, window_seconds=60),
}

DEFAULT_CONFIG = RateLimitConfig(limit=60, window_seconds=60)


def get_config(endpoint: str) -> RateLimitConfig:
    path = endpoint.split('?')[0].rstrip('/')
    return ENDPOINT_LIMITS.get(path, DEFAULT_CONFIG)
