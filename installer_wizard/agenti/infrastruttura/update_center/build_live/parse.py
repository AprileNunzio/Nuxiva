from __future__ import annotations

import re
from typing import Any, Dict, Optional

EVENTS = frozenset({"start", "unit", "beat", "done", "fail"})
MAX_LINE = 256
MAX_UNITS = 100_000
_PKG = re.compile(r"^[a-z][a-z0-9\-]{1,47}$")
_NAME = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")
_VERSION = re.compile(r"^v[0-9A-Za-z.+\-]{1,40}$")


def _count(raw: str) -> Optional[int]:
    if not raw.isascii() or not raw.isdigit() or len(raw) > 6:
        return None
    value = int(raw)
    return value if value <= MAX_UNITS else None


def _crate(parts: list[str]) -> Optional[str]:
    if not parts or not _NAME.match(parts[0]):
        return None
    if len(parts) > 1 and _VERSION.match(parts[1]):
        return f"{parts[0]} {parts[1]}"
    return parts[0]


def parse(raw: str) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, str) or len(raw) > MAX_LINE:
        return None
    parts = raw.split()
    if len(parts) < 4 or parts[0] not in EVENTS or not _PKG.match(parts[1]):
        return None
    done, total = _count(parts[2]), _count(parts[3])
    if done is None or total is None:
        return None
    return {"event": parts[0], "pkg": parts[1], "n": done, "total": total, "crate": _crate(parts[4:6])}
