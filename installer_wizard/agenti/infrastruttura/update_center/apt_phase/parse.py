from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Dict, Optional

try:
    import nuxiva_native as _native
except ImportError:
    _native = None

_REQUIRED = ("update_apt_line", "update_apt_percent")
RUST = _native is not None and all(hasattr(_native, name) for name in _REQUIRED)
ENGINE = "rust" if RUST else "python"

MAX_LINE = 220
MAX_PACKAGE = 100
MAX_INPUT = 64 * 1024
KINDS = frozenset({"fetch", "read", "summary", "unpack", "setup", "trigger", "warn", "error", "other"})
_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b.")
_PACKAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+\-]*$")
_SUMMARY = {
    "upgraded": re.compile(r"(\d+) upgraded,"),
    "installed": re.compile(r"(\d+) newly installed"),
    "removed": re.compile(r"(\d+) to remove"),
    "held": re.compile(r"(\d+) not upgraded"),
}


def _bounded(raw: str) -> str:
    return raw[:MAX_INPUT]


def _redact(token: str) -> str:
    scheme, sep, rest = token.partition("://")
    if not sep:
        return token
    rest = re.split(r"[?#]", rest, maxsplit=1)[0]
    authority, slash, path = rest.partition("/")
    host = authority.rsplit("@", 1)[-1]
    marker = "***@" if "@" in authority else ""
    return f"{scheme}://{marker}{host}{slash}{path}"


def _truncate(text: str) -> str:
    data = text.encode("utf-8")
    if len(data) <= MAX_LINE:
        return text
    return data[:MAX_LINE].decode("utf-8", errors="ignore") + "…"


def _py_sanitize(raw: str) -> str:
    segments = [s for s in raw.split("\r") if s.strip()]
    last = segments[-1] if segments else ""
    last = _ESCAPE.sub("", last).replace("\t", " ")
    last = "".join(c for c in last if unicodedata.category(c) != "Cc")
    tokens = [_redact(t) if "://" in t else t for t in last.split()]
    return _truncate(" ".join(tokens))


def _package(raw: Optional[str]) -> Optional[str]:
    token = (raw or "").split(":", 1)[0]
    return token if 0 < len(token) <= MAX_PACKAGE and _PACKAGE.match(token) else None


def _summary(text: str) -> Optional[Dict[str, int]]:
    if " upgraded, " not in text or " newly installed" not in text:
        return None
    found = {key: pattern.search(text) for key, pattern in _SUMMARY.items()}
    if found["upgraded"] is None:
        return None
    return {key: int(match.group(1)) if match else 0 for key, match in found.items()}


def _after(text: str, prefix: str) -> Optional[str]:
    return text[len(prefix):].lstrip() if text.startswith(prefix) else None


def _first(text: str) -> Optional[str]:
    parts = text.split()
    return parts[0] if parts else None


def _py_classify(raw: str) -> Dict[str, Any]:
    text = _py_sanitize(_bounded(raw))
    package = summary = None
    if text.startswith(("Get:", "Hit:", "Ign:", "Err:")):
        kind = "warn" if text.startswith("Err:") else "fetch"
    elif (rest := _after(text, "Unpacking ")) is not None:
        kind, package = "unpack", _package(_first(rest))
    elif (rest := _after(text, "Setting up ")) is not None:
        kind, package = "setup", _package(_first(rest))
    elif (rest := _after(text, "Processing triggers for ")) is not None:
        kind, package = "trigger", _package(_first(rest))
    elif text.startswith(("E: ", "dpkg: error")):
        kind = "error"
    elif text.startswith(("W: ", "N: ")):
        kind = "warn"
    elif text.startswith(("Reading ", "Building ", "Calculating ", "Fetched ")):
        kind = "read"
    elif (summary := _summary(text)) is not None:
        kind = "summary"
    else:
        kind = "other"
    return {"kind": kind, "text": text, "package": package, "summary": summary}


def _py_percent(summary: Optional[Dict[str, int]], unpacked: int, configured: int) -> int:
    if not summary:
        return 0
    total = int(summary.get("upgraded", 0)) + int(summary.get("installed", 0))
    if total <= 0:
        return 100
    return min(100, (max(0, unpacked) + max(0, configured)) * 100 // (total * 2))


def classify(raw: str) -> Dict[str, Any]:
    if RUST:
        data = json.loads(_native.update_apt_line(_bounded(raw)))
        return data if isinstance(data, dict) and data.get("kind") in KINDS else _py_classify(raw)
    return _py_classify(raw)


def percent(summary: Optional[Dict[str, int]], unpacked: int, configured: int) -> int:
    if RUST:
        return int(_native.update_apt_percent(json.dumps(summary), max(0, unpacked), max(0, configured)))
    return _py_percent(summary, unpacked, configured)
