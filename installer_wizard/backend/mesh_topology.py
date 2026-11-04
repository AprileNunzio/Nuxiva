from __future__ import annotations

import time
from typing import Any, Callable, Dict, Iterable, List, Optional

PAIRED_KIND = {
    "server": "compute",
    "desktop": "compute",
    "satellite": "satellite",
    "display": "satellite",
    "esp32": "micro",
    "sensor": "micro",
    "android": "mobile",
    "other": "satellite",
}


def paired_nodes() -> List[Dict[str, Any]]:
    from features.nodes.registry import registry

    return registry.listing()


def paired_source() -> Callable[[], List[Dict[str, Any]]]:
    return paired_nodes


def _number(value: Any) -> Optional[float]:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _paired_view(node: Dict[str, Any], mesh: Any, parent: Optional[str]) -> Dict[str, Any]:
    hardware = node.get("hardware") if isinstance(node.get("hardware"), dict) else {}
    metrics = node.get("metrics") if isinstance(node.get("metrics"), dict) else {}
    ram_total = _number(hardware.get("ram_gb"))
    ram_percent = _number(metrics.get("ram"))
    last_seen = _number(node.get("last_seen")) or None
    name = mesh.display_name(node["id"], node.get("name"))
    return {
        "id": node["id"],
        "name": name,
        "tier": node.get("type_label"),
        "type": PAIRED_KIND.get(node.get("type"), "satellite"),
        "ip": node.get("ip"),
        "parent_id": parent,
        "online": bool(node.get("online")),
        "source": "paired",
        "room": node.get("room") or None,
        "telemetry": {
            "node_id": node["id"],
            "name": name,
            "cpu_percent": _number(metrics.get("cpu")),
            "ram_total_gb": ram_total,
            "ram_used_gb": round(ram_total * ram_percent / 100, 1) if ram_total and ram_percent is not None else None,
            "temp_c": _number(metrics.get("temp")),
            "uptime_s": _number(metrics.get("uptime")),
            "cpu_cores": _number(hardware.get("cores")),
            "gpu_name": hardware.get("gpu") or None,
            "os": hardware.get("os") or None,
            "last_updated": last_seen,
        },
    }


def _merge(existing: Optional[Dict[str, Any]], incoming: Dict[str, Any]) -> Dict[str, Any]:
    if existing is None:
        return incoming
    telemetry = dict(existing.get("telemetry") or {})
    telemetry.update({k: v for k, v in incoming["telemetry"].items() if v is not None})
    return {**existing, **{k: v for k, v in incoming.items() if v is not None}, "telemetry": telemetry}


def known_node_ids(mesh: Any, paired: Iterable[Dict[str, Any]]) -> set:
    return {mesh.node_id, *mesh.peers.keys(), *(n["id"] for n in paired)}


def compose_topology(mesh: Any, paired: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    state = mesh.get_mesh_canvas_state()
    paired_list = list(paired)
    nodes: Dict[str, Dict[str, Any]] = {node["id"]: node for node in state["nodes"]}
    known = set(nodes) | {n["id"] for n in paired_list}
    for node in paired_list:
        parent = mesh.resolve_parent(node["id"], mesh.node_id, known)
        nodes[node["id"]] = _merge(nodes.get(node["id"]), _paired_view(node, mesh, parent))
    local = nodes.get(mesh.node_id)
    if local is not None:
        local["online"] = True
        local["source"] = "local"
    links = [
        {"source": node.get("parent_id") or "virtual-core", "target": node_id}
        for node_id, node in nodes.items()
        if node_id != mesh.node_id
    ]
    return {"nodes": list(nodes.values()), "links": links, "timestamp": time.time()}
