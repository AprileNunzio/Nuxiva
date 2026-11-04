import asyncio
import json
import time
import logging
from typing import Any

try:
    from .delivery import enqueue, close_delivery
except ImportError:
    from delivery import enqueue, close_delivery

logger = logging.getLogger("nuxiva.ear.broadcast")

SESSIONS: set = set()


def register(session: Any) -> None:
    SESSIONS.add(session)


def unregister(session: Any) -> None:
    SESSIONS.discard(session)
    close_delivery(session)
    stream = getattr(session, "input", None)
    if stream is not None:
        stream.stop()


def all_sessions() -> set:
    return SESSIONS


async def broadcast_event(origin: Any = None, **event: Any) -> None:
    raw = dict(event)
    data = json.dumps(raw)
    mirror = json.dumps({**raw, "origin": False}) if "origin" not in raw else data
    now = time.time()
    for session in list(SESSIONS):
        if raw.get("type") == "level" and origin is not None and session is not origin and getattr(session, "last_pcm_time", 0.0) > now - 2.5:
            continue
        target = data if origin is None or session is origin else mirror
        enqueue(session, raw.get("type", ""), target)
    await asyncio.sleep(0)


async def send_event(session, **event):
    enqueue(session, event.get("type", ""), json.dumps(event))
    await asyncio.sleep(0)


async def park_hidden() -> None:
    visible = [s for s in SESSIONS if getattr(s, "page", {}).get("visible") == "visible"]
    if not visible:
        return
    for s in list(SESSIONS):
        if getattr(s, "page", {}).get("visible") == "hidden":
            try:
                await s.ws.close(4001, "pagina nascosta")
            except (RuntimeError, OSError) as exc:
                logger.debug("Hidden ear client already closed: %s", exc)
