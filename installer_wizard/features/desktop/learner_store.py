import hashlib
import hmac
import logging
import os
import re
import secrets
from pathlib import Path

from config import STATE_DIR

log = logging.getLogger("nuxiva.desktop.learner")
KEY_LEN = 32
MAX_BLOB = 4 * 1024 * 1024
PSEUDONYM = re.compile(r"^[0-9a-f]{64}$")
LABEL = b"nuxiva.display.learner.pseudonym.v1:"


def folder() -> Path:
    return STATE_DIR / "display_learner"


def profiles() -> Path:
    return folder() / "profiles"


def _write(path: Path, data: bytes) -> None:
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


def master() -> bytes:
    path = folder() / "master.key"
    try:
        key = path.read_bytes()
    except FileNotFoundError:
        key = secrets.token_bytes(KEY_LEN)
        _write(path, key)
    if path.stat().st_mode & 0o077:
        path.chmod(0o600)
    if len(key) != KEY_LEN or not any(key):
        raise ValueError("learner.key.invalid")
    return key


def pseudonym(slug: str, key: bytes) -> str:
    return hmac.new(key, LABEL + slug.strip().lower().encode(), hashlib.sha256).hexdigest()


def _path(person: str) -> Path:
    if not PSEUDONYM.match(person):
        raise ValueError("learner.person.invalid")
    return profiles() / f"{person}.bin"


def save(person: str, blob: bytes) -> None:
    if len(blob) > MAX_BLOB:
        raise ValueError("learner.profile.too_large")
    _write(_path(person), blob)


def delete(person: str) -> bool:
    path = _path(person)
    existed = path.exists()
    path.unlink(missing_ok=True)
    return existed


def stored() -> list[tuple[str, bytes]]:
    base = profiles()
    if not base.is_dir():
        return []
    out = []
    for path in sorted(base.glob("*.bin")):
        person = path.stem
        if not PSEUDONYM.match(person) or path.stat().st_size > MAX_BLOB:
            log.error("Profilo di apprendimento ignorato perché non valido: %s", path.name)
            continue
        out.append((person, path.read_bytes()))
    return out


def quarantine(person: str) -> None:
    path = _path(person)
    if path.exists():
        path.replace(path.with_suffix(".corrupt"))
