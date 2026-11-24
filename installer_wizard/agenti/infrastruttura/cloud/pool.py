import asyncio
import weakref

import httpx

LIMITS = httpx.Limits(max_connections=32, max_keepalive_connections=16, keepalive_expiry=90.0)
DEFAULT_TIMEOUT = httpx.Timeout(120.0, connect=10.0)
_clients: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, httpx.AsyncClient]" = weakref.WeakKeyDictionary()


def shared() -> httpx.AsyncClient:
    loop = asyncio.get_running_loop()
    found = _clients.get(loop)
    if found is None or found.is_closed:
        found = httpx.AsyncClient(limits=LIMITS, timeout=DEFAULT_TIMEOUT, follow_redirects=False)
        _clients[loop] = found
    return found


async def close() -> None:
    loop = asyncio.get_running_loop()
    found = _clients.pop(loop, None)
    if found is not None and not found.is_closed:
        await found.aclose()
