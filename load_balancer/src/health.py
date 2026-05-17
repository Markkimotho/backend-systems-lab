import asyncio
import logging
import os
import aiohttp
from .pool import BackendServer, ServerStatus

log = logging.getLogger(__name__)

INTERVAL = int(os.getenv('HEALTH_CHECK_INTERVAL', '5'))
THRESHOLD = 3   # failures before marking unhealthy
RECOVERY = 3    # successes before marking healthy again


class HealthChecker:
    def __init__(self, servers: list[BackendServer], interval: int = INTERVAL):
        self.servers = servers
        self.interval = interval
        self._task: asyncio.Task | None = None

    async def _check_one(self, server: BackendServer, session: aiohttp.ClientSession) -> None:
        if server.status == ServerStatus.DRAINING:
            return
        try:
            timeout = aiohttp.ClientTimeout(total=2)
            async with session.get(f'{server.address}/health', timeout=timeout) as resp:
                if resp.status == 200:
                    was_unhealthy = not server.is_healthy
                    server.mark_success()
                    if was_unhealthy:
                        log.info('[health] %s recovered', server.address)
                else:
                    server.mark_failure(THRESHOLD)
                    if not server.is_healthy:
                        log.warning('[health] %s marked UNHEALTHY (status %d)',
                                    server.address, resp.status)
        except Exception as e:
            prev = server.is_healthy
            server.mark_failure(THRESHOLD)
            if prev and not server.is_healthy:
                log.warning('[health] %s marked UNHEALTHY (%s)', server.address, type(e).__name__)

    async def _loop(self) -> None:
        async with aiohttp.ClientSession() as session:
            while True:
                await asyncio.gather(*[self._check_one(s, session) for s in self.servers])
                await asyncio.sleep(self.interval)

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        if self._task:
            self._task.cancel()
