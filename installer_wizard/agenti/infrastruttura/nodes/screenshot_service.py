import asyncio
import itertools
import logging
import time

from agenti.nodes import screenshot_bridge, screenshot_local

log = logging.getLogger("nuxiva.screenshot")
DAEMON_WAIT = 4.0
STEP = 0.2
_seq = itertools.count()
_lock = asyncio.Lock()


async def _daemon(previous: int) -> dict | None:
    try:
        screenshot_bridge.request()
    except screenshot_bridge.BridgeUnavailable:
        return None
    waited = 0.0
    while waited < DAEMON_WAIT:
        await asyncio.sleep(STEP)
        waited += STEP
        report = screenshot_bridge.latest()
        if report and report["id"] > previous and report["status"] != "delivered_later":
            return report
    return None


async def take() -> dict:
    async with _lock:
        before = screenshot_bridge.latest()
        report = await _daemon(before["id"] if before else 0)
        if report:
            return report
        log.warning("Servizio screenshot nativo assente o muto: cattura diretta dal supervisore")
        try:
            result = await asyncio.to_thread(screenshot_local.capture, next(_seq))
        except screenshot_local.LocalError as exc:
            log.warning("Screenshot diretto non riuscito: %s", exc)
            result = {"status": exc.status, "name": "", "folder": ""}
        return screenshot_bridge.record({**result, "id": int(time.time() * 1000), "count": 0})
