import logging
import threading

from config import ETC_DIR, STATE_DIR, read_env
from cryptography.fernet import InvalidToken
from sealed import SealedFile

from features.hands import native

log = logging.getLogger("nuxiva.hands")
SEALED = SealedFile(STATE_DIR / "hands.vault", ETC_DIR / "hands.key")
_lock = threading.Lock()
_state = {"revision": 0, "profile": None}


def _legacy(profile: dict) -> dict:
    env = read_env()
    if env.get("NUXIVA_HANDS_COUNT") == "1":
        profile["bindings"] = [b for b in profile.get("bindings", []) if not str(b.get("gesture", "")).startswith("duo.")]
    return profile


def _read() -> dict:
    try:
        stored = SEALED.load()
    except (InvalidToken, ValueError, OSError) as exc:
        log.warning("Profilo gesti illeggibile, uso quello predefinito: %s", exc)
        stored = {}
    if not native.available():
        return stored
    try:
        return native.normalize(stored) if stored else _legacy(native.defaults())
    except ValueError as exc:
        log.warning("Profilo gesti non valido, uso quello predefinito: %s", exc)
        return native.defaults()


def load() -> dict:
    with _lock:
        if _state["profile"] is None:
            _state["profile"] = _read()
        return _state["profile"]


def revision() -> int:
    with _lock:
        return _state["revision"]


def save(profile: object) -> dict:
    if not isinstance(profile, dict):
        raise ValueError("hands_invalid_profile")
    clean = native.normalize(profile)
    with _lock:
        SEALED.save(clean)
        _state["profile"] = clean
        _state["revision"] += 1
    return clean


def reset() -> dict:
    return save(native.defaults())
