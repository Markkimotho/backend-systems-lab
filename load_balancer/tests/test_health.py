import pytest
import asyncio
import aiohttp
from load_balancer.src.pool import BackendServer, ServerStatus
from load_balancer.src.health import HealthChecker


@pytest.mark.asyncio
async def test_healthy_server_stays_healthy():
    """If a server's /health returns 200, it stays healthy."""
    # This test requires a mock server on a port — uses aiohttp test server
    from aiohttp import web

    async def health_handler(request):
        return web.Response(text='OK')

    app = web.Application()
    app.router.add_get('/health', health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 19001)
    await site.start()

    try:
        server = BackendServer(host='127.0.0.1', port=19001)
        checker = HealthChecker([server], interval=1)

        async with aiohttp.ClientSession() as session:
            await checker._check_one(server, session)
            assert server.is_healthy
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_unhealthy_after_failures():
    """Server that can't be reached becomes UNHEALTHY after threshold failures."""
    server = BackendServer(host='127.0.0.1', port=19999)  # nothing running here
    checker = HealthChecker([server], interval=1)

    async with aiohttp.ClientSession() as session:
        for _ in range(3):
            await checker._check_one(server, session)
        assert not server.is_healthy
        assert server.status == ServerStatus.UNHEALTHY
