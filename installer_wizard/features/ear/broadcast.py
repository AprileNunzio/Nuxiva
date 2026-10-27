import json
import logging
from typing import Any

import websockets

logger = logging.getLogger("nuxiva.ear.broadcast")

SESSIONS: set = set()


def register(session: Any) -> None:
    SESSIONS.add(session)


def unregister(session: Any) -> None:
    SESSIONS.discard(session)


def all_sessions() -> set:
    return SESSIONS


async def broadcast_event(origin: Any = None, **event: Any) -> None:
    raw = dict(event)
    data = json.dumps(raw)
    mirror = json.dumps({**raw, "origin": False}) if "origin" not in raw else data
    for s in list(SESSIONS):
        try:
            target_data = data if (origin is None or s is origin) else mirror
            await s.ws.send(target_data)
        except (websockets.ConnectionClosed, RuntimeError, Exception):
            pass


async def park_hidden() -> None:
    visible = [s for s in SESSIONS if getattr(s, "page", {}).get("visible") == "visible"]
    if not visible:
        return
    for s in list(SESSIONS):
        if getattr(s, "page", {}).get("visible") == "hidden":
            try:
                await s.ws.close(4001, "pagina nascosta")
            except Exception:
                pass
