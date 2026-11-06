import importlib
import json
import logging
import re
import threading
import time
from pathlib import Path

import native_core
from config import STATE_DIR

log = logging.getLogger("nuxiva.native")
BUILD_FILE = STATE_DIR / "native" / "build.json"
WHEEL_FILE = STATE_DIR / "native" / "wheel.json"
RELOAD_FILE = STATE_DIR / "native" / "reload.json"
RELOAD_GUARD_SECONDS = 900.0
STATES = frozenset({"building", "ready", "failed", "disabled"})
STAGES = frozenset({"wheel", "egress", "netguard", "agency", "display", "done"})
RETRY_SECONDS = 15.0
_lock = threading.Lock()
_last_try = {"at": 0.0}
_loaded: dict = {"module": None, "identity": None, "warned": False}
REV = re.compile(r"^[0-9a-f]{7,64}$")


def disabled() -> bool:
    return native_core.disabled()


def _import():
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


def _identity(loaded) -> tuple | None:
    path = getattr(loaded, "__file__", None)
    if not isinstance(path, str) or not path:
        return None
    target = Path(path)
    files = sorted(target.parent.glob("*.so")) if target.name == "__init__.py" else [target]
    if not files:
        return None
    try:
        return tuple((f.name, st.st_ino, st.st_size, st.st_mtime_ns) for f in files for st in (f.stat(),))
    except OSError:
        return ("missing",)


def _wheel_rev() -> str:
    try:
        raw = json.loads(WHEEL_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return ""
    except (OSError, ValueError) as exc:
        log.warning("Revisione del modulo nativo installato illeggibile: %s", exc)
        return ""
    return _rev(raw) if isinstance(raw, dict) else ""


def _remember(loaded) -> None:
    if _loaded["module"] is loaded:
        return
    _loaded.update(module=loaded, identity=_identity(loaded), warned=False)


def replaced() -> bool:
    loaded = _loaded["module"]
    if loaded is None or _loaded["identity"] is None:
        return False
    return _identity(loaded) != _loaded["identity"]


def behind() -> bool:
    record = _record()
    if record.get("state") not in ("building", "failed") or record.get("stage") != "wheel":
        return False
    current = _rev(record)
    return bool(current) and current != _wheel_rev()


def stale() -> bool:
    return _loaded["module"] is not None and (replaced() or behind())


def reload_needed() -> bool:
    return not disabled() and replaced()


def claim_reload(now: float | None = None) -> bool:
    loaded = _loaded["module"]
    target = _identity(loaded) if loaded is not None else None
    if not target or target == ("missing",):
        return False
    mark = json.dumps(target)
    now = time.time() if now is None else now
    try:
        previous = json.loads(RELOAD_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        previous = {}
    except (OSError, ValueError) as exc:
        log.warning("Registro dei riavvii per il modulo nativo illeggibile: %s", exc)
        previous = {}
    if isinstance(previous, dict) and previous.get("target") == mark \
            and isinstance(previous.get("at"), (int, float)) and now - previous["at"] < RELOAD_GUARD_SECONDS:
        return False
    RELOAD_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = RELOAD_FILE.with_name(f".reload.{threading.get_ident()}")
    tmp.write_text(json.dumps({"target": mark, "at": now}), encoding="utf-8")
    tmp.replace(RELOAD_FILE)
    return True


def module():
    if disabled():
        return None
    loaded = _import()
    if loaded is None:
        return None
    _remember(loaded)
    if not stale():
        return loaded
    if not _loaded["warned"]:
        _loaded["warned"] = True
        log.warning("Modulo nativo caricato in memoria diverso da quello installato: "
                    "uso il motore Python finché il supervisore non lo ricarica")
    return None


def python_fallback(area: str) -> None:
    native_core.python_fallback(area)


def feature(name: str):
    loaded = module()
    return getattr(loaded, name, None) if loaded is not None else None


def _record() -> dict:
    try:
        raw = json.loads(BUILD_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        log.warning("Stato della compilazione nativa illeggibile: %s", exc)
        return {}
    return raw if isinstance(raw, dict) else {}


def _rev(record: dict) -> str:
    rev = record.get("rev")
    return rev if isinstance(rev, str) and REV.match(rev) else ""


def build_status() -> dict:
    if disabled():
        return {"state": "disabled", "stage": None, "at": None}
    raw = _record()
    if reload_needed():
        return {"state": "restarting", "stage": None, "at": raw.get("at") if isinstance(raw.get("at"), (int, float)) else None}
    if not raw:
        return {"state": "unknown", "stage": None, "at": None}
    state = raw.get("state") if raw.get("state") in STATES else "unknown"
    stage = raw.get("stage") if raw.get("stage") in STAGES else None
    at = raw.get("at") if isinstance(raw.get("at"), (int, float)) else None
    return {"state": state, "stage": stage, "at": at}


def availability(name: str) -> dict:
    present = feature(name) is not None
    return {"native": present, "build": build_status()}
