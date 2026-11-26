import json
import os
import secrets
import tempfile
import threading
import time
from pathlib import Path

import native_core
from config import ETC_DIR, STATE_DIR, env_get

ROOT = Path(STATE_DIR) / "reasoning"
KEY = Path(ETC_DIR) / "reasoning.key"
JOURNAL = ROOT / "journal"
LEDGER = ROOT / "ledger.json"
SWITCH = ROOT / "switch.json"
CONFIG = ROOT / "config.json"
JOURNAL_DAYS = 7
MAX_FILE = 256 * 1024
_lock = threading.Lock()
_engine = None


class Unavailable(RuntimeError):
    pass


def now_ms() -> int:
    return int(time.time() * 1000)


def emergency_off() -> bool:
    return env_get("NUXIVA_REASON_MODE", "").strip().lower() == "off"


def _read(path: Path) -> str | None:
    if not path.exists():
        return None
    if path.stat().st_size > MAX_FILE:
        raise ValueError(f"reasoning.{path.stem}.too_large")
    return path.read_text(encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.chmod(temp, 0o600)
        os.replace(temp, path)
    except OSError:
        Path(temp).unlink(missing_ok=True)
        raise


def key() -> bytes:
    if KEY.exists():
        data = KEY.read_bytes()
        if len(data) != 32:
            raise ValueError("reasoning.key")
        return data
    data = secrets.token_bytes(32)
    KEY.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(KEY, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
    return data


def ready() -> bool:
    return native_core.symbol("RustReasonEngine") is not None


def engine():
    global _engine
    with _lock:
        if _engine is not None:
            return _engine
        factory = native_core.symbol("RustReasonEngine")
        if factory is None:
            raise Unavailable("native_unavailable")
        built = factory(_read(CONFIG))
        ledger = _read(LEDGER)
        if ledger:
            built.load_ledger(ledger)
        switch = _read(SWITCH)
        if switch:
            built.restore(switch)
        if emergency_off():
            built.kill()
        _engine = built
        return built


def save() -> None:
    current = engine()
    _write(LEDGER, current.ledger())
    _write(SWITCH, json.dumps(json.loads(current.status(now_ms()))["switch"]))


def save_config(raw: str) -> None:
    engine().configure(raw)
    _write(CONFIG, raw)


def journal_dir() -> str:
    JOURNAL.mkdir(parents=True, exist_ok=True, mode=0o700)
    cutoff = time.time() - JOURNAL_DAYS * 86400
    for item in JOURNAL.glob("*.journal"):
        if item.stat().st_mtime < cutoff:
            item.unlink(missing_ok=True)
    return str(JOURNAL)


def reload() -> None:
    global _engine
    with _lock:
        _engine = None
