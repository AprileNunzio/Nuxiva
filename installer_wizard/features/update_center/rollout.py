from __future__ import annotations

from typing import Any, Dict, Iterable, List


def node_rollout_view(nodes: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    view = []
    for node in nodes:
        pending = "update" in (node.get("commands") or [])
        view.append({
            "id": node["id"],
            "name": node.get("name") or node["id"],
            "type": node.get("type"),
            "room": node.get("room") or None,
            "online": bool(node.get("online")),
            "version": node.get("version") or None,
            "last_seen": node.get("last_seen") or None,
            "update_queued": pending,
        })
    return view


def queue_updates(registry: Any, node_ids: Iterable[str]) -> List[str]:
    known = registry.data.get("nodes", {})
    queued = []
    for node_id in node_ids:
        if node_id in known:
            registry.command(node_id, "update")
            queued.append(node_id)
    return queued
