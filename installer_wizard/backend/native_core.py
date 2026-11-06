import logging
import os
import threading

log = logging.getLogger("nuxiva.native")
_warned: set[str] = set()
_lock = threading.Lock()


def disabled() -> bool:
    return os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0"


def load():
    if disabled():
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    return nuxiva_native


def symbol(name: str):
    loaded = load()
    return getattr(loaded, name, None) if loaded is not None else None


def python_fallback(area: str) -> None:
    with _lock:
        if area in _warned:
            return
        _warned.add(area)
    log.warning("Sezione %s: uso il motore Python deprecato perché il modulo Rust non è disponibile", area)
