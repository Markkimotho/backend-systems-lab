import asyncio
import logging
import os
import signal
from .store import Store
from .resp import parse_resp, encode_resp, encode_hello
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
    proto = 2  # negotiated RESP version; HELLO bumps it to 3 for modern clients
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

            # --- HELLO: protocol negotiation handshake ---
            # redis-py (RESP3 by default since v5) and redis-cli -3 send HELLO
            # on connect. Without it the client connection fails and the whole
            # pipeline 500s. HELLO [protover [AUTH user pass] [SETNAME name]].
            # It runs before the auth gate because it can carry AUTH itself.
            if name == 'HELLO':
                new_proto = proto
                if len(cmd) > 1:
                    try:
                        new_proto = int(cmd[1])
                    except (ValueError, TypeError):
                        writer.write(b"-NOPROTO unsupported protocol version\r\n")
                        await writer.drain()
                        continue
                    if new_proto not in (2, 3):
                        writer.write(b"-NOPROTO unsupported protocol version\r\n")
                        await writer.drain()
                        continue
                # Optional inline AUTH: HELLO <proto> AUTH <user> <pass>
                i = 2
                while i < len(cmd):
                    opt = cmd[i].upper() if isinstance(cmd[i], str) else ''
                    if opt == 'AUTH' and i + 2 < len(cmd):
                        if REQUIREPASS and cmd[i + 2] == REQUIREPASS:
                            authenticated = True
                        elif REQUIREPASS:
                            writer.write(b'-WRONGPASS invalid username-password pair or user is disabled.\r\n')
                            await writer.drain()
                            break
                        i += 3
                    else:
                        i += 1
                else:
                    if not authenticated:
                        writer.write(b'-NOAUTH HELLO must be called with the client already authenticated, otherwise the HELLO <proto> AUTH <user> <pass> option can be used to authenticate the client and select the RESP protocol version at the same time\r\n')
                        await writer.drain()
                        continue
                    proto = new_proto
                    writer.write(encode_hello(proto))
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
                    resp_bytes = await dispatch(queued, store, proto)
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

            response = await dispatch(cmd, store, proto)
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
