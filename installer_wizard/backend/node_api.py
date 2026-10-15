"""Nuxiva OS v5.0.0 — Node Plane Backend API.

Manages node hardware modules, provisioning targets, and node telemetry.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v5/nodes", tags=["Node Plane"])
admin_routes = router

# In-memory storage for node app configurations
_NODE_APP_CONFIGS: Dict[str, Dict[str, Any]] = {}

AVAILABLE_NODE_APPS = [
    {"id": "brain", "name": "Brain", "icon": "Cpu", "category": "node_plane"},
    {"id": "audio", "name": "Audio", "icon": "Volume2", "category": "node_plane"},
    {"id": "mic", "name": "Mic", "icon": "Mic", "category": "node_plane"},
    {"id": "camera", "name": "Camera", "icon": "Camera", "category": "node_plane"},
    {"id": "printers", "name": "Printers", "icon": "Printer", "category": "node_plane"},
    {"id": "bluetooth", "name": "Bluetooth", "icon": "Bluetooth", "category": "node_plane"},
    {"id": "display", "name": "Display", "icon": "Monitor", "category": "node_plane"},
    {"id": "whiteboard", "name": "Whiteboard", "icon": "Edit3", "category": "node_plane"},
    {"id": "client_link", "name": "Client Link", "icon": "Smartphone", "category": "node_plane"},
]

DEFAULT_NODES = [
    {
        "id": "node-pc-master",
        "name": "PC-Workstation-i9",
        "tier": "Tier-1 Compute",
        "ip": "192.168.1.10",
        "os": "Linux x86_64",
        "is_virtual_core": True,
        "status": "online",
        "metrics": {"cpu": 18.4, "ram": "5.4/32GB", "temp": 46.2, "ping": 1.2}
    },
    {
        "id": "node-rpi-cam",
        "name": "RaspberryPi-5-LivingRoom",
        "tier": "Tier-2 Satellite",
        "ip": "192.168.1.15",
        "os": "Linux arm64",
        "is_virtual_core": False,
        "status": "online",
        "metrics": {"cpu": 12.1, "ram": "1.2/8GB", "temp": 41.5, "ping": 2.4}
    },
    {
        "id": "node-esp32-sensor",
        "name": "ESP32-S3-Studio",
        "tier": "Tier-3 ESP32",
        "ip": "192.168.1.55",
        "os": "FreeRTOS",
        "is_virtual_core": False,
        "status": "online",
        "metrics": {"cpu": 3.0, "ram": "180KB", "temp": 32.0, "ping": 6.8}
    }
]


class ConfigUpdateRequest(BaseModel):
    settings: Dict[str, Any] = {}
    enabled: bool = True


class ProvisionRequest(BaseModel):
    target: str  # pc | raspberry | esp32 | android
    parent_ip: str = "192.168.1.10"
    wifi_ssid: str = ""
    wifi_key: str = ""


@router.get("")
def list_nodes() -> List[Dict[str, Any]]:
    try:
        from server.features.mesh_coordinator.p2p_mesh import p2p_mesh
        canvas = p2p_mesh.get_mesh_canvas_state()
        return canvas.get("nodes", [])
    except Exception:
        import socket
        return [{
            "id": socket.gethostname(),
            "name": socket.gethostname(),
            "tier": "Tier-1 (Host & Virtual Core)",
            "type": "compute",
            "ip": "127.0.0.1",
            "status": "online"
        }]


@router.get("/{node_id}")
def get_node(node_id: str) -> Dict[str, Any]:
    try:
        from server.features.mesh_coordinator.p2p_mesh import p2p_mesh
        telem = p2p_mesh.get_node_telemetry(node_id)
        return {
            "id": node_id,
            "name": telem.get("name", node_id),
            "tier": telem.get("tier", "Tier-1 (Compute & Virtual Core)"),
            "ip": telem.get("ip", "127.0.0.1"),
            "os": telem.get("os", "Linux"),
            "is_virtual_core": True,
            "status": "online",
            "metrics": {
                "cpu": telem.get("cpu_percent", 0.0),
                "ram": f"{telem.get('ram_used_gb', 0)}/{telem.get('ram_total_gb', 0)}GB",
                "temp": telem.get("temp_c", 0.0),
                "ping": telem.get("ping_ms", 0.1)
            }
        }
    except Exception:
        import socket
        return {
            "id": node_id,
            "name": socket.gethostname(),
            "tier": "Tier-1 Compute",
            "ip": "127.0.0.1",
            "os": "Linux",
            "is_virtual_core": True,
            "status": "online",
            "metrics": {"cpu": 0.0, "ram": "N/A", "temp": 0.0, "ping": 0.1}
        }


@router.get("/{node_id}/apps")
def list_node_apps(node_id: str) -> List[Dict[str, Any]]:
    return AVAILABLE_NODE_APPS


@router.get("/{node_id}/apps/{app_id}")
def get_node_app_config(node_id: str, app_id: str) -> Dict[str, Any]:
    key = f"{node_id}:{app_id}"
    config = _NODE_APP_CONFIGS.get(key, {
        "nodeId": node_id,
        "appId": app_id,
        "enabled": True,
        "settings": {},
        "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    })
    return config


@router.post("/{node_id}/apps/{app_id}/config")
def update_node_app_config(node_id: str, app_id: str, req: ConfigUpdateRequest) -> Dict[str, Any]:
    key = f"{node_id}:{app_id}"
    config = {
        "nodeId": node_id,
        "appId": app_id,
        "enabled": req.enabled,
        "settings": req.settings,
        "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    _NODE_APP_CONFIGS[key] = config
    return config


@router.post("/{node_id}/reboot")
def reboot_node(node_id: str) -> Dict[str, Any]:
    return {
        "nodeId": node_id,
        "action": "reboot",
        "status": "initiated",
        "timestamp": time.time()
    }


@router.post("/{node_id}/provision")
def provision_node(node_id: str, req: ProvisionRequest) -> Dict[str, Any]:
    valid_targets = {"pc", "raspberry", "esp32", "android"}
    if req.target not in valid_targets:
        raise HTTPException(status_code=400, detail=f"Invalid target '{req.target}'. Must be one of {valid_targets}")

    return {
        "nodeId": node_id,
        "target": req.target,
        "parent_ip": req.parent_ip,
        "provisioning_token": f"nux-prov-{node_id}-{int(time.time())}",
        "status": "ready"
    }
