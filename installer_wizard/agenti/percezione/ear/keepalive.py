import asyncio
import logging
import time
from collections.abc import Awaitable, Callable

log = logging.getLogger("nuxiva.ear")

FIRST_DELAY = 2.0
MAX_DELAY = 60.0
HEALTHY_AFTER = 120.0


async def supervise(name: str, task: Callable[[], Awaitable[object]]) -> None:
    delay = FIRST_DELAY
    while True:
        started = time.monotonic()
        try:
            await task()
            return
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Attività «%s» interrotta da un errore: la riavvio tra %.0f s", name, delay)
        if time.monotonic() - started > HEALTHY_AFTER:
            delay = FIRST_DELAY
        await asyncio.sleep(delay)
        delay = min(delay * 2, MAX_DELAY)
