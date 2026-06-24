from .store import Store
from .resp import encode_resp


async def dispatch(cmd: list, store: Store, proto: int = 2) -> bytes:
    """
    Route a parsed RESP command list to the correct handler.
    All commands are uppercase-normalized before matching.
    Unknown commands return a RESP error.

    `proto` is the connection's negotiated RESP version (2 or 3). It only
    changes how null replies are encoded; every other reply is identical
    across protocols. HELLO/AUTH/MULTI are handled in the server loop because
    they mutate per-connection state.
    """
    if not cmd:
        return b'-ERR empty command\r\n'

    name = cmd[0].upper()

    try:
        if name == 'PING':
            msg = cmd[1] if len(cmd) > 1 else 'PONG'
            return encode_resp(msg, proto)

        elif name == 'ECHO':
            if len(cmd) < 2:
                return b'-ERR wrong number of arguments\r\n'
            return encode_resp(cmd[1], proto)

        elif name == 'SET':
            # SET key value [EX seconds] [PX milliseconds]
            if len(cmd) < 3:
                return b'-ERR wrong number of arguments\r\n'
            key, value = cmd[1], cmd[2]
            kwargs = {}
            i = 3
            while i < len(cmd):
                opt = cmd[i].upper()
                if opt == 'EX' and i + 1 < len(cmd):
                    kwargs['ex'] = int(cmd[i + 1])
                    i += 2
                elif opt == 'PX' and i + 1 < len(cmd):
                    kwargs['px'] = int(cmd[i + 1])
                    i += 2
                else:
                    i += 1
            store.set(key, value, **kwargs)
            return encode_resp('OK', proto)

        elif name == 'GET':
            if len(cmd) < 2:
                return b'-ERR wrong number of arguments\r\n'
            return encode_resp(store.get(cmd[1]), proto)

        elif name == 'INCR':
            if len(cmd) < 2:
                return b'-ERR wrong number of arguments\r\n'
            return encode_resp(store.incr(cmd[1]), proto)

        elif name == 'INCRBY':
            if len(cmd) < 3:
                return b'-ERR wrong number of arguments\r\n'
            key = cmd[1]
            amount = int(cmd[2])
            return encode_resp(store.incrby(key, amount), proto)

        elif name == 'DEL':
            if len(cmd) < 2:
                return b'-ERR wrong number of arguments\r\n'
            return encode_resp(store.delete(*cmd[1:]), proto)

        elif name == 'EXISTS':
            if len(cmd) < 2:
                return b'-ERR wrong number of arguments\r\n'
            return encode_resp(store.exists(*cmd[1:]), proto)

        elif name == 'EXPIRE':
            if len(cmd) < 3:
                return b'-ERR wrong number of arguments\r\n'
            nx = len(cmd) > 3 and cmd[3].upper() == 'NX'
            return encode_resp(store.expire(cmd[1], int(cmd[2]), nx=nx), proto)

        elif name == 'TTL':
            if len(cmd) < 2:
                return b'-ERR wrong number of arguments\r\n'
            return encode_resp(store.ttl(cmd[1]), proto)

        elif name == 'DBSIZE':
            return encode_resp(store.dbsize(), proto)

        elif name == 'FLUSHALL' or name == 'FLUSHDB':
            store.flush()
            return encode_resp('OK', proto)

        elif name == 'COMMAND':
            # redis client sends COMMAND DOCS on connect — return empty array
            return encode_resp([], proto)

        elif name == 'CLIENT':
            # redis client sends CLIENT SETINFO — acknowledge it
            return encode_resp('OK', proto)

        elif name == 'CONFIG':
            # redis client may send CONFIG GET — return empty list
            return encode_resp([], proto)

        else:
            return f'-ERR unknown command `{name}`\r\n'.encode()

    except Exception as e:
        return f'-ERR {e}\r\n'.encode()
