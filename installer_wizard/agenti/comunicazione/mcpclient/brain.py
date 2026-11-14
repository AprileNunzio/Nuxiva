import json
import logging
import threading

import native_core
from config import AGENTS_DIR, env_get

from agenti.mcpclient import engine

log = logging.getLogger("nuxiva.brain")
MAX_TEXT = 8192
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


def dispatch(text: str, principal: str, now_ms: int) -> dict | None:
    if not enabled() or not isinstance(text, str) or not text or len(text) > MAX_TEXT:
        return None
    brain = get()
    if brain is None:
        return None
    try:
        return json.loads(brain.dispatch(text, str(principal or "guest"), int(now_ms)))
    except ValueError as error:
        log.warning("dispatch del motore centrale rifiutato: %s", error)
        return {"kind": "rejected", "error": str(error)}
