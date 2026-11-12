import json
import os
import re
from pathlib import Path

from agenti.sentinel import vault

DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_DAY_FILE = 512 * 1024 * 1024


def root() -> Path:
    return vault.root() / "memory"


def _dir(name: str) -> Path:
    path = root() / name
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    return path


def _day(day: str) -> str:
    if not DAY.match(day):
        raise vault.VaultError("sentinel.memory.day.invalid")
    return day


def day_path(day: str) -> Path:
    return _dir("days") / f"{_day(day)}.mem"


def key_path(day: str) -> Path:
    return _dir("keys") / f"{_day(day)}.key"


def read_day(day: str) -> bytes:
    path = day_path(day)
    if not path.exists():
        return b""
    if path.stat().st_size > MAX_DAY_FILE:
        raise vault.VaultError("sentinel.memory.day.too_large")
    return path.read_bytes()


def append_day(day: str, frame: bytes) -> None:
    fd = os.open(day_path(day), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "ab") as handle:
        handle.write(frame)
        handle.flush()
        os.fsync(handle.fileno())


def replace_day(day: str, data: bytes) -> None:
    vault.private_write(day_path(day), data)


def set_aside(day: str, valid_len: int) -> None:
    path = day_path(day)
    data = path.read_bytes()
    vault.private_write(path.with_suffix(".torn"), data[valid_len:])
    vault.private_write(path, data[:valid_len])


def wrapped_key(day: str, create) -> bytes:
    path = key_path(day)
    try:
        return path.read_bytes()
    except FileNotFoundError:
        vault.private_write(path, create(day))
        return path.read_bytes()


def days() -> list[str]:
    return sorted(p.stem for p in _dir("keys").glob("*.key") if DAY.match(p.stem))


def destroy(day: str) -> None:
    for path in (key_path(day), day_path(day)):
        path.unlink(missing_ok=True)


def save_policy(data: dict) -> None:
    vault.private_write(root() / "policy.json", json.dumps(data).encode())


def load_policy() -> dict | None:
    path = root() / "policy.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None
