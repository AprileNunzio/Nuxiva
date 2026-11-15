from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional

from . import fleet, history


def _epoch(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value).timestamp()
        except ValueError:
            return None
    return None


def _last_installed() -> Optional[float]:
    stamps = [float(r.get("installed_at") or 0) for r in history.load_history() if r.get("status") == "installed"]
    return max(stamps) if stamps and max(stamps) > 0 else None


def server_input(info: Mapping[str, Any], *, version: Optional[str], auto_update: bool, active: bool,
                 next_check: Optional[float]) -> Dict[str, Any]:
    success = _epoch(info.get("last_success")) or _last_installed()
    failure = info.get("last_failure") if isinstance(info.get("last_failure"), dict) else None
    error = info.get("check_error") or None
    if not error and failure:
        failed_at = _epoch(failure.get("at")) or 0.0
        if success is None or failed_at > success:
            error = str(failure.get("code") or "failed")
    return {"version": version, "state": "installing" if active else "idle", "available": bool(info.get("available")),
            "auto_update": auto_update, "last_check": _epoch(info.get("last_check")), "last_success": success,
            "last_error": error, "next_check": next_check}


def node_input(nodes: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    keys = ("id", "name", "type", "online", "version", "update", "update_history")
    return [{key: node.get(key) for key in keys if key in node} for node in nodes]


def build(server: Dict[str, Any], nodes: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    return fleet.overview({"now": time.time(), "server": server, "nodes": node_input(nodes)})
