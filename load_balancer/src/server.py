import asyncio
import logging
import os
import signal
import uuid
import aiohttp
from aiohttp import web
import redis.asyncio as aioredis
from .pool import BackendServer
from .algorithms import RoundRobin
from .health import HealthChecker
from .session import SessionRouter

log = logging.getLogger(__name__)

REDIS_URL = f"redis://{os.getenv('REDIS_HOST', '127.0.0.1')}:{os.getenv('REDIS_PORT', '6380')}"
PORT = int(os.getenv('LOAD_BALANCER_PORT', '8090'))

FORWARD_TIMEOUT = aiohttp.ClientTimeout(
    total=int(os.getenv('FORWARD_TIMEOUT', '30')),
    connect=int(os.getenv('CONNECT_TIMEOUT', '5')),
)

SERVERS = [
    BackendServer(
        host=os.getenv('SERVER_1_HOST', '127.0.0.1'),
        port=int(os.getenv('SERVER_1_PORT', '8001')),
    ),
    BackendServer(
        host=os.getenv('SERVER_2_HOST', '127.0.0.1'),
        port=int(os.getenv('SERVER_2_PORT', '8002')),
    ),
    BackendServer(
        host=os.getenv('SERVER_3_HOST', '127.0.0.1'),
        port=int(os.getenv('SERVER_3_PORT', '8003')),
    ),
]


async def create_app() -> web.Application:
    redis_client = aioredis.from_url(REDIS_URL)
    router = RoundRobin()
    sessions = SessionRouter(redis_client)
    health = HealthChecker(SERVERS)
    connector = aiohttp.TCPConnector(limit=500)
    http_session = aiohttp.ClientSession(
        connector=connector,
        cookie_jar=aiohttp.DummyCookieJar(),
    )

    async def handle(request: web.Request) -> web.Response:
        session_id = request.cookies.get('session_id')
        pinned_server: BackendServer | None = None

        if session_id:
            pinned_address = await sessions.get_server(session_id)
            if pinned_address:
                pinned_server = next(
                    (s for s in SERVERS if s.address == pinned_address and s.is_healthy),
                    None,
                )
                if not pinned_server:
                    await sessions.clear_session(session_id)

        body = await request.read()
        forward_headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in ('host', 'content-length')
        }

        attempted: set[BackendServer] = set()

        # Retry up to len(SERVERS) times on connection-level failures.
        # A connection failure means the backend never received the request,
        # so retrying is safe regardless of HTTP method.
        for _ in range(len(SERVERS)):
            if pinned_server and pinned_server not in attempted:
                server = pinned_server
            else:
                available = [s for s in SERVERS if s not in attempted]
                try:
                    server = router.pick(available)
                except RuntimeError:
                    break
                # Re-pin the session to the newly selected server
                session_id = session_id or str(uuid.uuid4())
                await sessions.pin_session(session_id, server.address)

            attempted.add(server)
            server.active_connections += 1
            try:
                async with http_session.request(
                    request.method,
                    f'{server.address}{request.path_qs}',
                    headers=forward_headers,
                    data=body if body else None,
                    allow_redirects=False,
                    timeout=FORWARD_TIMEOUT,
                ) as resp:
                    response_body = await resp.read()
                    response = web.Response(
                        status=resp.status,
                        body=response_body,
                        headers={'X-Served-By': server.address},
                    )
                    session_id = session_id or str(uuid.uuid4())
                    response.set_cookie('session_id', session_id, max_age=3600)
                    return response

            except aiohttp.ClientConnectorError:
                server.mark_failure()
                log.warning('Connection failed to %s — trying next server', server.address)
                continue  # retry with another server

            except asyncio.TimeoutError:
                log.warning('Request to %s timed out after %ds',
                            server.address, FORWARD_TIMEOUT.total)
                return web.Response(status=504, text='Gateway Timeout')

            finally:
                server.active_connections -= 1

        return web.Response(status=503, text='Service Unavailable — no healthy servers')

    app = web.Application()
    app.router.add_route('*', '/{path_info:.*}', handle)

    async def startup(app_):
        health.start()

    async def cleanup(app_):
        health.stop()
        await http_session.close()
        await redis_client.aclose()

    app.on_startup.append(startup)
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
    log.info('Load balancer running on port %d', PORT)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    await stop.wait()
    log.info('Load balancer shutting down gracefully...')
    await runner.cleanup()


if __name__ == '__main__':
    asyncio.run(main())
