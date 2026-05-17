import asyncio
import logging
import os
import signal
import aiohttp
from aiohttp import web
import redis.asyncio as aioredis
from .limiter import RateLimiter
from .config import get_config

log = logging.getLogger(__name__)

REDIS_URL = f"redis://{os.getenv('REDIS_HOST', '127.0.0.1')}:{os.getenv('REDIS_PORT', '6380')}"
UPSTREAM = f"http://{os.getenv('LOAD_BALANCER_HOST', '127.0.0.1')}:{os.getenv('LOAD_BALANCER_PORT', '8090')}"
PORT = int(os.getenv('RATE_LIMITER_PORT', '8080'))

FORWARD_TIMEOUT = aiohttp.ClientTimeout(
    total=int(os.getenv('FORWARD_TIMEOUT', '30')),
    connect=int(os.getenv('CONNECT_TIMEOUT', '5')),
)


async def create_app() -> web.Application:
    redis_client = aioredis.from_url(REDIS_URL)
    connector = aiohttp.TCPConnector(limit=200)
    http_session = aiohttp.ClientSession(
        connector=connector,
        cookie_jar=aiohttp.DummyCookieJar(),
    )

    async def handle(request: web.Request) -> web.Response:
        # Use the real peer IP, not the spoofable X-Forwarded-For header.
        # request.remote is the direct TCP connection address and cannot be
        # forged by external clients.
        ip = request.remote or '0.0.0.0'
        endpoint = request.path
        config = get_config(endpoint)

        limiter = RateLimiter(redis_client, config)
        allowed, remaining, retry_after, reset_at = await limiter.is_allowed(ip, endpoint)

        if not allowed:
            return web.Response(
                status=429,
                text='Too Many Requests',
                headers={
                    'X-RateLimit-Limit':     str(config.limit),
                    'X-RateLimit-Remaining': '0',
                    'Retry-After':           str(retry_after),
                    'X-RateLimit-Reset':     str(reset_at),  # Unix timestamp per RFC 6585
                },
            )

        # Forward to load balancer
        try:
            forward_headers = {
                k: v for k, v in request.headers.items()
                if k.lower() not in ('host', 'content-length')
            }
            forward_headers['X-Forwarded-For'] = ip

            body = await request.read()
            async with http_session.request(
                request.method,
                f'{UPSTREAM}{request.path_qs}',
                headers=forward_headers,
                data=body if body else None,
                allow_redirects=False,
                timeout=FORWARD_TIMEOUT,
            ) as resp:
                response_body = await resp.read()
                response_headers = {
                    k: v for k, v in resp.headers.items()
                    if k.lower() != 'set-cookie'
                }
                response_headers['X-RateLimit-Limit'] = str(config.limit)
                response_headers['X-RateLimit-Remaining'] = str(remaining)
                response_headers['X-RateLimit-Reset'] = str(reset_at)
                response = web.Response(
                    status=resp.status,
                    body=response_body,
                    headers=response_headers,
                )
                # Forward Set-Cookie headers separately to preserve duplicates
                for cookie_header in resp.headers.getall('Set-Cookie', []):
                    response.headers.add('Set-Cookie', cookie_header)
                return response
        except asyncio.TimeoutError:
            log.warning('Timeout forwarding %s %s to upstream', request.method, request.path)
            return web.Response(status=504, text='Gateway Timeout')
        except aiohttp.ClientConnectorError:
            log.error('Cannot connect to upstream %s', UPSTREAM)
            return web.Response(status=502, text='Bad Gateway — upstream unavailable')

    app = web.Application()
    app.router.add_route('*', '/{path_info:.*}', handle)

    async def cleanup(app_):
        await http_session.close()
        await redis_client.aclose()

    app.on_cleanup.append(cleanup)
    return app


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    )
    app = await create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    log.info('Rate limiter running on port %d → upstream %s', PORT, UPSTREAM)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    await stop.wait()
    log.info('Rate limiter shutting down gracefully...')
    await runner.cleanup()


if __name__ == '__main__':
    asyncio.run(main())
