import asyncio
import logging
import os
import signal
from .store import Store
from .resp import parse_resp, encode_resp
from .commands import dispatch

log = logging.getLogger(__name__)

# REDIS_BIND: address this server binds to (0.0.0.0 in Docker, 127.0.0.1 locally)
# REDIS_HOST is for *clients* connecting to this server — not used here
BIND_HOST = os.getenv('REDIS_BIND', '0.0.0.0')
PORT = int(os.getenv('REDIS_PORT', '6380'))
REQUIREPASS = os.getenv('REQUIREPASS', '')
MAX_KEYS = int(os.getenv('MAX_KEYS', '0'))  # 0 = unlimited


async def handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    store: Store,
) -> None:
    authenticated = not bool(REQUIREPASS)  # skip auth when no password is set
    in_multi = False
    queued_cmds: list[list] = []
    try:
        while True:
            cmd = await parse_resp(reader)
            if cmd is None:
                break
            # Normalise: inline commands can be strings
            if isinstance(cmd, str):
                cmd = cmd.strip().split()
            if not isinstance(cmd, list):
                cmd = [cmd]

            if not cmd:
                writer.write(b'-ERR empty command\r\n')
                await writer.drain()
                continue

            name = cmd[0].upper() if isinstance(cmd[0], str) else str(cmd[0]).upper()

            # --- AUTH handling (must work before authentication check) ---
            if name == 'AUTH':
                if not REQUIREPASS:
                    writer.write(b'-ERR Client sent AUTH, but no password is set\r\n')
                elif len(cmd) < 2:
                    writer.write(b'-ERR wrong number of arguments\r\n')
                elif cmd[1] == REQUIREPASS:
                    authenticated = True
                    writer.write(encode_resp('OK'))
                else:
                    writer.write(b'-WRONGPASS invalid username-password pair or user is disabled.\r\n')
                await writer.drain()
                continue

            # --- Reject unauthenticated clients ---
            if not authenticated:
                writer.write(b'-NOAUTH Authentication required.\r\n')
                await writer.drain()
                continue

            if name == 'MULTI':
                in_multi = True
                queued_cmds = []
                writer.write(encode_resp('OK'))
                await writer.drain()
                continue

            if name == 'EXEC':
                if not in_multi:
                    writer.write(b'-ERR EXEC without MULTI\r\n')
                    await writer.drain()
                    continue
                results = []
                for queued in queued_cmds:
                    resp_bytes = await dispatch(queued, store)
                    results.append(resp_bytes)
                # Encode as RESP array of raw responses
                header = f'*{len(results)}\r\n'.encode()
                writer.write(header + b''.join(results))
                in_multi = False
                queued_cmds = []
                await writer.drain()
                continue

            if name == 'DISCARD':
                if not in_multi:
                    writer.write(b'-ERR DISCARD without MULTI\r\n')
                    await writer.drain()
                    continue
                in_multi = False
                queued_cmds = []
                writer.write(encode_resp('OK'))
                await writer.drain()
                continue

            if in_multi:
                queued_cmds.append(cmd)
                writer.write(b'+QUEUED\r\n')
                await writer.drain()
                continue

            response = await dispatch(cmd, store)
            writer.write(response)
            await writer.drain()
    except (asyncio.IncompleteReadError, ConnectionResetError, BrokenPipeError):
        pass  # client disconnected
    except Exception as e:
        try:
            writer.write(f'-ERR server error: {e}\r\n'.encode())
            await writer.drain()
        except Exception:
            pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    )
    store = Store(max_keys=MAX_KEYS)
    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, store),
        host=BIND_HOST,
        port=PORT,
        limit=2**16,  # 64KB read buffer per connection
    )
    log.info('Redis clone listening on %s:%d (max_keys=%s, auth=%s)',
             BIND_HOST, PORT, MAX_KEYS or 'unlimited', bool(REQUIREPASS))

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    async with server:
        await stop.wait()
    log.info('Redis clone stopped')


if __name__ == '__main__':
    asyncio.run(main())
