import asyncio
import json
import logging
import threading

import native_core
from config import AGENTS_DIR, env_get

from agenti.mcpclient import engine, planner

log = logging.getLogger("nuxiva.brain")
MAX_TEXT = 8192
TIMEOUT = 60.0
_lock = threading.RLock()
_brain = None


def enabled() -> bool:
    return env_get("NUXIVA_BRAIN_ENGINE", "off").strip().lower() == "rust"


def available() -> bool:
    return native_core.symbol("RustBrain") is not None


def get(planner=None):
    global _brain
    with _lock:
        if _brain is None:
            cls = native_core.symbol("RustBrain")
            if cls is None:
                return None
            _brain = cls(engine.get(), str(AGENTS_DIR), planner)
        return _brain


def reset() -> None:
    global _brain
    with _lock:
        brain, _brain = _brain, None
    if brain is not None:
        brain.cancel()


def dispatch(text: str, principal: str, now_ms: int, loop=None) -> dict | None:
    if not enabled() or not isinstance(text, str) or not text or len(text) > MAX_TEXT:
        return None
    brain = get(planner.make(loop, str(principal or "")) if loop is not None else None)
    if brain is None:
        return None
    try:
        return json.loads(brain.dispatch(text, str(principal or "guest"), int(now_ms)))
    except ValueError as error:
        log.warning("dispatch del motore centrale rifiutato: %s", error)
        return {"kind": "rejected", "error": str(error)}


async def attempt(text: str, principal: str, now_ms: int) -> dict | None:
    if not enabled():
        return None
    loop = asyncio.get_running_loop()
    try:
        outcome = await asyncio.wait_for(asyncio.to_thread(dispatch, text, principal, now_ms, loop), TIMEOUT)
    except (asyncio.TimeoutError, OSError, RuntimeError) as error:
        log.warning("motore centrale non disponibile, uso il percorso attuale: %s", error)
        return None
    if not isinstance(outcome, dict) or outcome.get("kind") != "executed":
        return None
    reply = str(outcome.get("text") or "").strip()
    if outcome.get("succeeded") and reply:
        return {"reply": reply, "ui": {"mode": "face"}, "intent": "brain", "agent": "motore centrale", "elapsed_ms": 0}
    if outcome.get("acted"):
        return {"reply": "", "failed": True, "intent": "brain", "agent": "motore centrale", "elapsed_ms": 0}
    return None
