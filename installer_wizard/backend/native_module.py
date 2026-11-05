import importlib
import json
import logging
import os
import threading
import time

from config import STATE_DIR

log = logging.getLogger("nuxiva.native")
BUILD_FILE = STATE_DIR / "native" / "build.json"
STATES = frozenset({"building", "ready", "failed", "disabled"})
STAGES = frozenset({"wheel", "egress", "netguard", "agency", "display", "done"})
RETRY_SECONDS = 15.0
_lock = threading.Lock()
_last_try = {"at": 0.0}


def disabled() -> bool:
    return os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0"


def module():
    if disabled():
        return None
    try:
        import nuxiva_native
        return nuxiva_native
    except ImportError:
        pass
    with _lock:
        now = time.monotonic()
        if now - _last_try["at"] < RETRY_SECONDS:
            return None
        _last_try["at"] = now
    importlib.invalidate_caches()
    try:
        import nuxiva_native
    except ImportError:
        return None
    log.info("Modulo nativo caricato senza riavviare il supervisore")
    return nuxiva_native


def feature(name: str):
    loaded = module()
    return getattr(loaded, name, None) if loaded is not None else None


def build_status() -> dict:
    if disabled():
        return {"state": "disabled", "stage": None, "at": None}
    try:
        raw = json.loads(BUILD_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"state": "unknown", "stage": None, "at": None}
    except (OSError, ValueError) as exc:
        log.warning("Stato della compilazione nativa illeggibile: %s", exc)
        return {"state": "unknown", "stage": None, "at": None}
    if not isinstance(raw, dict):
        return {"state": "unknown", "stage": None, "at": None}
    state = raw.get("state") if raw.get("state") in STATES else "unknown"
    stage = raw.get("stage") if raw.get("stage") in STAGES else None
    at = raw.get("at") if isinstance(raw.get("at"), (int, float)) else None
    return {"state": state, "stage": stage, "at": at}


def availability(name: str) -> dict:
    present = feature(name) is not None
    return {"native": present, "build": build_status()}
