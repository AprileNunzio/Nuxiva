from __future__ import annotations

import json
import math
import re
import unicodedata
from typing import Any, Dict, List, Optional

from . import native

MAX_VERSION = 40
MAX_CODE = 48
MAX_NODES = 512
MAX_HISTORY = 20
FUTURE_SKEW = 86400.0
STATES = ("idle", "checking", "downloading", "installing", "awaiting_user", "failed", "rolled_back")
CHANNELS = ("debian", "android", "windows", "esp32", "other")
ACTIVE = ("checking", "downloading", "installing")
_VERSION = re.compile(r"^[A-Za-z0-9._+\-]{1,%d}$" % MAX_VERSION)
_CODE = re.compile(r"^[A-Za-z0-9._\-]{1,%d}$" % MAX_CODE)
_ID = re.compile(r"^[A-Za-z0-9_\-]{1,48}$")


def _rust() -> bool:
    return native.RUST and hasattr(native._native, "update_fleet_overview") and hasattr(native._native, "update_fleet_sanitize")


def _token(value: Any, pattern: re.Pattern) -> Optional[str]:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text if pattern.fullmatch(text) else None


def _code(value: Any) -> Optional[str]:
    text = _token(value, _CODE)
    return text.lower() if text else None


def _stamp(value: Any, now: float) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if math.isfinite(number) and 0 < number <= now + FUTURE_SKEW:
        return float(math.floor(number))
    return None


def _number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) and number > 0 else None


def _text(value: Any, limit: int) -> Optional[str]:
    if not isinstance(value, str):
        return None
    clean = "".join(ch for ch in value if unicodedata.category(ch) != "Cc")[:limit].strip()
    return clean or None


def _py_sanitize(raw: Any, now: float) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    state = raw.get("state")
    if state not in STATES:
        return None
    channel = raw.get("channel")
    error = raw.get("last_error")
    failure = None
    if isinstance(error, dict):
        error_code = _code(error.get("code"))
        if error_code:
            failure = {"code": error_code, "at": _stamp(error.get("at"), now)}
    return {"state": state, "channel": channel if channel in CHANNELS else "other",
            "version": _token(raw.get("version"), _VERSION), "target": _token(raw.get("target"), _VERSION),
            "last_check": _stamp(raw.get("last_check"), now), "last_success": _stamp(raw.get("last_success"), now),
            "last_error": failure}


def sanitize(raw: Any, now: float) -> Optional[Dict[str, Any]]:
    if _rust():
        found = native._native.update_fleet_sanitize(json.dumps(raw), float(now))
        return json.loads(found) if found else None
    return _py_sanitize(raw, now)


def _node_status(online: bool, version: Optional[str], server: Optional[str], update: Optional[Dict[str, Any]]) -> str:
    if not online:
        return "offline"
    state = update["state"] if update else "idle"
    if state in ("failed", "rolled_back"):
        return "failed"
    if state in ACTIVE:
        return "updating"
    if state == "awaiting_user":
        return "awaiting_user"
    if version is None:
        return "unknown"
    return "outdated" if server and version != server else "up_to_date"


def _server_status(state: str, has_error: bool, available: bool) -> str:
    if state in ACTIVE:
        return "updating"
    if has_error:
        return "failed"
    return "outdated" if available else "up_to_date"


def _history(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    out = []
    for entry in value:
        if not isinstance(entry, dict) or entry.get("state") not in STATES:
            continue
        out.append({"at": _number(entry.get("at")), "state": entry["state"],
                    "version": _token(entry.get("version"), _VERSION), "code": _code(entry.get("code"))})
    return out[::-1][:MAX_HISTORY]


def _node_view(node: Any, server: Optional[str], now: float) -> Optional[Dict[str, Any]]:
    if not isinstance(node, dict):
        return None
    node_id = _token(node.get("id"), _ID)
    if not node_id:
        return None
    online = node.get("online") is True
    update = _py_sanitize(node["update"], now) if "update" in node else None
    reported = _token(node.get("version"), _VERSION) or (update["version"] if update else None)
    return {"id": node_id, "name": _text(node.get("name"), 60) or node_id, "type": _text(node.get("type"), 32),
            "online": online, "version": reported, "status": _node_status(online, reported, server, update),
            "update": update, "history": _history(node.get("update_history"))}


def _py_overview(data: Dict[str, Any]) -> Dict[str, Any]:
    now = _number(data.get("now")) or 0.0
    server = data.get("server") if isinstance(data.get("server"), dict) else {}
    version = _token(server.get("version"), _VERSION)
    state = server.get("state") if server.get("state") in STATES else "idle"
    error = _text(server.get("last_error"), 160)
    available = server.get("available") is True
    status = _server_status(state, error is not None, available)
    server_view = {"version": version, "state": state, "status": status, "available": available,
                   "auto_update": server.get("auto_update") is True, "last_check": _number(server.get("last_check")),
                   "last_success": _number(server.get("last_success")), "last_error": error,
                   "next_check": _number(server.get("next_check"))}
    raw = data.get("nodes") if isinstance(data.get("nodes"), list) else []
    nodes = [view for view in (_node_view(item, version, now) for item in raw[:MAX_NODES]) if view]

    def count(name: str) -> int:
        return sum(1 for node in nodes if node["status"] == name)

    counts = {"total": len(nodes), "up_to_date": count("up_to_date"), "outdated": count("outdated"),
              "updating": count("updating"), "failed": count("failed"), "awaiting_user": count("awaiting_user"),
              "offline": count("offline"), "unknown": count("unknown")}
    if status == "failed" or counts["failed"]:
        summary = "attention"
    elif status == "updating" or counts["updating"]:
        summary = "updating"
    elif status == "outdated" or counts["outdated"] + counts["awaiting_user"]:
        summary = "outdated"
    else:
        summary = "up_to_date"
    return {"summary": summary, "server": server_view, "nodes": nodes, "counts": counts}


def overview(data: Dict[str, Any]) -> Dict[str, Any]:
    if _rust():
        return json.loads(native._native.update_fleet_overview(json.dumps(data)))
    return _py_overview(data)
