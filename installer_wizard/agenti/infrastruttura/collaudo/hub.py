import json
import os
import secrets
import threading

import native_core
from agenti.collaudo import paths
from agenti.collaudo.pyhub import PyHub

_lock = threading.Lock()
_hub = None


def _secure(path, mode: int) -> None:
    os.chmod(path, mode)


def key_hex() -> str:
    paths.ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    _secure(paths.ROOT, 0o700)
    if paths.KEY_FILE.exists():
        value = paths.KEY_FILE.read_text(encoding="utf-8").strip()
        if len(value) == 64:
            return value
    value = secrets.token_hex(32)
    tmp = paths.KEY_FILE.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(value)
    os.replace(tmp, paths.KEY_FILE)
    return value


def native() -> bool:
    return native_core.symbol("RustCollaudo") is not None


def get():
    global _hub
    with _lock:
        if _hub is None:
            engine = native_core.symbol("RustCollaudo")
            if engine is not None:
                _hub = engine(str(paths.LOG_DIR), key_hex(), paths.SEGMENT_BYTES, paths.KEEP_SEGMENTS)
            else:
                native_core.python_fallback("collaudo")
                _hub = PyHub(paths.PY_LOG_DIR, key_hex(), paths.SEGMENT_BYTES, paths.KEEP_SEGMENTS)
            if paths.MODE_FILE.exists():
                _hub.set_collaudo(paths.MODE_FILE.read_text(encoding="utf-8").strip() == "1")
        return _hub


def reset() -> None:
    global _hub
    with _lock:
        _hub = None


def emit(raw: dict):
    return get().emit(json.dumps(raw, separators=(",", ":"), default=str))


def query(args: dict) -> list[dict]:
    return json.loads(get().query(json.dumps(args)))


def set_mode(enabled: bool) -> None:
    paths.ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    paths.MODE_FILE.write_text("1" if enabled else "0", encoding="utf-8")
    get().set_collaudo(enabled)


def report(args: dict, spec: list | None = None) -> dict:
    return json.loads(get().report(json.dumps(args), None if spec is None else json.dumps(spec)))
