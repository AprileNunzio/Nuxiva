import json
import os
import re
import stat
from pathlib import Path

RUNTIME = Path(os.environ.get("NUXIVA_SCREENSHOT_RUNTIME", "/run/nuxiva-screenshot"))
REQUEST = "request"
STATUS = "status.json"
MAX_STATUS = 4096
STATUSES = frozenset({"saved", "queued", "blocked", "failed", "disabled", "no_target", "delivered_later"})
NAME = re.compile(r"^[a-z0-9-]{1,40}_\d{8}-\d{6}_\d{3}\.png$")
_cache: dict = {"mtime": None, "value": None}
_memory: dict = {"value": None}


class BridgeUnavailable(OSError):
    pass


def request(root: Path | None = None) -> None:
    base = root or RUNTIME
    try:
        info = os.lstat(base)
    except FileNotFoundError as exc:
        raise BridgeUnavailable("service") from exc
    if not stat.S_ISDIR(info.st_mode):
        raise BridgeUnavailable("unsafe")
    fd = os.open(base / REQUEST, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    os.close(fd)


def _clean(raw) -> dict | None:
    if not isinstance(raw, dict) or raw.get("status") not in STATUSES:
        return None
    try:
        ident, count = int(raw.get("id") or 0), int(raw.get("count") or 0)
    except (TypeError, ValueError):
        return None
    name = str(raw.get("name") or "")
    folder = "".join(c for c in str(raw.get("folder") or "") if c.isprintable())[:240]
    return {"id": ident, "status": raw["status"], "name": name if NAME.match(name) else "",
            "folder": folder, "count": max(0, min(count, 10_000))}


def record(raw: dict) -> dict:
    value = _clean(raw)
    if value is None:
        raise ValueError("screenshot_status")
    _memory["value"] = value
    return value


def latest(root: Path | None = None) -> dict | None:
    found = _from_file(root)
    memory = _memory["value"] if root is None else None
    if memory and (not found or memory["id"] > found["id"]):
        return memory
    return found


def _from_file(root: Path | None) -> dict | None:
    path = (root or RUNTIME) / STATUS
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_STATUS:
        return None
    if root is None and _cache["mtime"] == info.st_mtime_ns:
        return _cache["value"]
    try:
        value = _clean(json.loads(path.read_text(encoding="utf-8")))
    except ValueError:
        value = None
    if root is None:
        _cache.update(mtime=info.st_mtime_ns, value=value)
    return value
