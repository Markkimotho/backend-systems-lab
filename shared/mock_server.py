import asyncio
import logging
import sys
from aiohttp import web

log = logging.getLogger(__name__)

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
SERVER_ID = f'server-{PORT}'


async def handle(request: web.Request) -> web.Response:
    await asyncio.sleep(0.01)  # simulate 10ms processing
    return web.json_response({
        'server': SERVER_ID,
        'path': request.path,
        'method': request.method,
    })


async def health(request: web.Request) -> web.Response:
    return web.Response(text='OK')


app = web.Application()
app.router.add_route('*', '/health', health)
app.router.add_route('*', '/{path_info:.*}', handle)

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    )
    log.info('Mock server %s running on port %d', SERVER_ID, PORT)
    web.run_app(app, port=PORT, access_log=None)
