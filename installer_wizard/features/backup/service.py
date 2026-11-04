import asyncio
import hashlib
import json
import logging
import re
import secrets
import tarfile
import threading
import time
from pathlib import Path

from config import STATE_DIR, env_get
from sealed import write_private
from state import store

log = logging.getLogger("nuxiva.backup")
ROOT = STATE_DIR / "backups"
INDEX = ROOT / "index.json"
ID_RE = re.compile(r"^[0-9a-f]{12}$")
CHUNK = 1 << 20
CHECK_SECONDS = 600
_lock = threading.RLock()


def enabled() -> bool:
    return env_get("NUXIVA_BACKUP", "1") != "0"


def _int(key: str, default: int, low: int, high: int) -> int:
    try:
        return max(low, min(high, int(env_get(key, str(default)))))
    except ValueError:
        return default


def interval_hours() -> int:
    return _int("NUXIVA_BACKUP_HOURS", 24, 0, 24 * 30)


def keep() -> int:
    return _int("NUXIVA_BACKUP_KEEP", 7, 1, 100)


def _load() -> dict[str, dict]:
    if not INDEX.exists():
        return {}
    rows = json.loads(INDEX.read_text(encoding="utf-8"))
    return rows if isinstance(rows, dict) else {}


def _save(rows: dict[str, dict]) -> None:
    ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    write_private(INDEX, json.dumps(rows, ensure_ascii=False).encode())


def _path(backup_id: str) -> Path:
    if not ID_RE.fullmatch(backup_id):
        raise KeyError(backup_id)
    return ROOT / f"nuxiva-{backup_id}.tar.gz"


def _digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(CHUNK):
            sha.update(block)
    return sha.hexdigest()


def _skip(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
    if info.name.split("/")[1:2] == ["backups"] or not (info.isfile() or info.isdir()):
        return None
    return info


def _build(backup_id: str) -> dict:
    ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = _path(backup_id)
    partial = target.with_suffix(".part")
    with tarfile.open(partial, "w:gz") as archive:
        archive.add(STATE_DIR, arcname="state", filter=_skip)
    partial.chmod(0o600)
    partial.replace(target)
    return {"id": backup_id, "created": time.time(), "size": target.stat().st_size, "sha256": _digest(target)}


def _prune() -> None:
    with _lock:
        rows = _load()
        ordered = sorted(rows.values(), key=lambda row: row["created"], reverse=True)
        for stale in ordered[keep():]:
            _path(stale["id"]).unlink(missing_ok=True)
            rows.pop(stale["id"], None)
        _save(rows)


def _create_sync(kind: str) -> dict:
    row = {**_build(secrets.token_hex(6)), "kind": kind}
    with _lock:
        rows = _load()
        rows[row["id"]] = row
        _save(rows)
    _prune()
    return row


async def create(kind: str = "manual") -> dict:
    row = await asyncio.to_thread(_create_sync, kind)
    store.event("INFO", f"Backup creato ({kind}, {row['size']} byte)", "backup")
    return row


def listing() -> list[dict]:
    with _lock:
        rows = _load()
    return sorted((row for row in rows.values() if _path(row["id"]).exists()), key=lambda row: row["created"], reverse=True)


def path_of(backup_id: str) -> Path:
    with _lock:
        if backup_id not in _load():
            raise KeyError(backup_id)
    target = _path(backup_id)
    if not target.is_file():
        raise KeyError(backup_id)
    return target


async def verify(backup_id: str) -> dict:
    target = path_of(backup_id)
    expected = _load()[backup_id]["sha256"]
    actual = await asyncio.to_thread(_digest, target)
    return {"id": backup_id, "ok": secrets.compare_digest(expected, actual)}


def delete(backup_id: str) -> None:
    with _lock:
        rows = _load()
        if backup_id not in rows:
            raise KeyError(backup_id)
        _path(backup_id).unlink(missing_ok=True)
        rows.pop(backup_id)
        _save(rows)
    store.event("INFO", "Backup eliminato", "backup")


def status() -> dict:
    items = listing()
    return {"enabled": enabled(), "interval_hours": interval_hours(), "keep": keep(), "items": items,
            "total_size": sum(row["size"] for row in items), "next": _next(items)}


def _next(items: list[dict]) -> float | None:
    hours = interval_hours()
    if not enabled() or hours == 0:
        return None
    last = items[0]["created"] if items else 0
    return last + hours * 3600


async def tick() -> None:
    due = _next(listing())
    if due is not None and due <= time.time():
        try:
            await create("auto")
        except (OSError, tarfile.TarError) as exc:
            log.error("Backup automatico fallito: %s", exc)
            store.event("ERROR", f"Backup automatico fallito: {exc}", "backup")


async def run() -> None:
    while True:
        await tick()
        await asyncio.sleep(CHECK_SECONDS)
