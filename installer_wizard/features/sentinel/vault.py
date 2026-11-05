import json
import os
import re
import secrets
from pathlib import Path

from config import STATE_DIR

KEY_LEN = 32
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_DAY_FILE = 256 * 1024 * 1024


class VaultError(ValueError):
    pass


def root() -> Path:
    return STATE_DIR / "sentinel"


def _dir(name: str) -> Path:
    path = root() / name
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    return path


def _private_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def secret(name: str) -> bytes:
    path = root() / f"{name}.key"
    try:
        key = path.read_bytes()
    except FileNotFoundError:
        _private_write(path, secrets.token_bytes(KEY_LEN))
        key = path.read_bytes()
    if path.stat().st_mode & 0o077:
        path.chmod(0o600)
    if len(key) != KEY_LEN or not any(key):
        raise VaultError(f"sentinel.{name}.invalid")
    return key


def _day(day: str) -> str:
    if not DAY.match(day):
        raise VaultError("sentinel.day.invalid")
    return day


def day_path(day: str) -> Path:
    return _dir("days") / f"{_day(day)}.log"


def key_path(day: str) -> Path:
    return _dir("keys") / f"{_day(day)}.key"


def checkpoint_path(day: str) -> Path:
    return _dir("checkpoints") / f"{_day(day)}.sig"


def read_day(day: str) -> bytes:
    path = day_path(day)
    if not path.exists():
        return b""
    if path.stat().st_size > MAX_DAY_FILE:
        raise VaultError("sentinel.day.too_large")
    return path.read_bytes()


def append_day(day: str, frame: bytes) -> None:
    path = day_path(day)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "ab") as handle:
        handle.write(frame)
        handle.flush()
        os.fsync(handle.fileno())


def replace_day(day: str, data: bytes) -> None:
    _private_write(day_path(day), data)


def set_aside(day: str, valid_len: int) -> None:
    path = day_path(day)
    data = path.read_bytes()
    _private_write(path.with_suffix(f".torn.{secrets.token_hex(4)}"), data[valid_len:])
    _private_write(path, data[:valid_len])


def wrapped_key(day: str, create) -> bytes:
    path = key_path(day)
    try:
        return path.read_bytes()
    except FileNotFoundError:
        _private_write(path, create(day))
        return path.read_bytes()


def has_key(day: str) -> bool:
    return key_path(day).exists()


def write_checkpoint(day: str, payload: bytes) -> None:
    _private_write(checkpoint_path(day), payload)


def read_checkpoint(day: str) -> bytes | None:
    path = checkpoint_path(day)
    return path.read_bytes() if path.exists() else None


def days() -> list[str]:
    return sorted(p.stem for p in _dir("keys").glob("*.key") if DAY.match(p.stem))


def destroy(day: str) -> None:
    for path in (key_path(day), day_path(day), checkpoint_path(day)):
        path.unlink(missing_ok=True)


def save_retention(data: dict) -> None:
    _private_write(root() / "retention.json", json.dumps(data).encode())


def load_retention() -> dict | None:
    path = root() / "retention.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None
