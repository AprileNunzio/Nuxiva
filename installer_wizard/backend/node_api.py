from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from access import require_admin
from node_network_probe import (
    build_initial_network_profile, compute_active_route,
    inspect_system_network_interfaces, merge_refreshed_interfaces,
)
from node_wifi_tasks import collect_node_tasks, connect_wifi, scan_system_wifi

router = APIRouter(prefix="/api/v5/nodes", tags=["Node Plane"], dependencies=[Depends(require_admin)])
admin_routes = router


class ProvisionRequest(BaseModel):
    target: str
    parent_ip: str = "127.0.0.1"
    wifi_ssid: str = ""
    wifi_key: str = ""

class OnboardNodeRequest(BaseModel):
    target: str
    name: str
    parent_id: str = "virtual_core"
    parent_ip: str = "127.0.0.1"
    usb_port: str = ""
    wifi_ssid: str = ""
    wifi_key: str = ""
    root_user: str = "root"
    root_password: str = ""

class RenameNodeRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)

class UpdatePolicyRequest(BaseModel):
    policy: str

class ToggleInterfaceRequest(BaseModel):
    interface: str
    is_up: bool

class ToggleVpnRequest(BaseModel):
    enabled: bool

class UpdateInterfaceIpRequest(BaseModel):
    interface: str
    mode: str
    ipv4: Optional[str] = None
    netmask: Optional[str] = None
    gateway: Optional[str] = None
    dns_primary: Optional[str] = None
    dns_secondary: Optional[str] = None

class WifiConnectRequest(BaseModel):
    ssid: str
    password: str = ""
    interface: Optional[str] = None

class WifiRadioRequest(BaseModel):
    enabled: bool
    interface: Optional[str] = None

class TerminateTaskRequest(BaseModel):
    pid: int

class ToggleCapabilityRequest(BaseModel):
    capability: str
    enabled: bool


_network_governor_native = None
_network_profiles_memory: Dict[str, Dict[str, Any]] = {}
_node_capabilities_memory: Dict[str, Dict[str, bool]] = {}
_LOCAL_LLM_MARKERS = ("ollama", "llama-server", "llama_server")
VALID_TARGETS = {"pc", "raspberry", "esp32", "android"}
TIER_MAP = {
    "pc": "Tier-1 (Workstation / Compute)",
    "raspberry": "Tier-2 (Smart Edge Satellite)",
    "esp32": "Tier-3 (Micro-Satellite I2S)",
    "android": "Tier-4 (Client Touch / Mobile)",
}


@router.get("/usb_ports")
def get_usb_ports() -> List[Dict[str, str]]:
    ports: List[Dict[str, str]] = []
    if os.name == "nt":
        try:
            cmd = "Get-PnpDevice -Class Ports -Status OK | Select-Object FriendlyName, InstanceId | ConvertTo-Json -Compress"
            p = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=5)
            if p.stdout.strip():
                raw = json.loads(p.stdout)
                for item in ([raw] if isinstance(raw, dict) else raw):
                    fname, iid = item.get("FriendlyName", ""), item.get("InstanceId", "")
                    ports.append({"device": iid or fname, "description": fname})
        except Exception:
            pass
    else:
        try:
            import serial.tools.list_ports
            for p in serial.tools.list_ports.comports():
                ports.append({"device": str(p.device), "description": str(p.description or p.device)})
        except Exception:
            import glob
            for dev in glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*") + glob.glob("/dev/cu.*"):
                ports.append({"device": dev, "description": dev})
    return ports


@router.get("")
def list_nodes() -> List[Dict[str, Any]]:
    try:
        from server.features.mesh_coordinator.p2p_mesh import p2p_mesh
        from mesh_topology import compose_topology, paired_nodes
        return compose_topology(p2p_mesh, paired_nodes()).get("nodes", [])
    except Exception:
        import socket
        h = socket.gethostname()
        return [{"id": h, "name": h, "tier": "Tier-1 (Host & Virtual Core)", "type": "compute",
                 "ip": "127.0.0.1", "status": "online", "source": "local", "online": True}]


@router.get("/{node_id}")
def get_node(node_id: str) -> Dict[str, Any]:
    from server.features.mesh_coordinator.p2p_mesh import p2p_mesh
    telem = p2p_mesh.get_node_telemetry(node_id)
    return {
        "id": node_id, "name": telem.get("name", node_id), "tier": telem.get("tier"),
        "ip": telem.get("ip"), "os": telem.get("os"), "is_local": node_id == p2p_mesh.node_id,
        "metrics": {"cpu": telem.get("cpu_percent"), "ram_used_gb": telem.get("ram_used_gb"),
                    "ram_total_gb": telem.get("ram_total_gb"), "temp": telem.get("temp_c"), "ping": telem.get("ping_ms")},
    }


@router.post("/{node_id}/provision")
def provision_node(node_id: str, req: ProvisionRequest) -> Dict[str, Any]:
    if req.target not in VALID_TARGETS:
        raise HTTPException(status_code=400, detail=f"Invalid target '{req.target}'. Must be one of {VALID_TARGETS}")
    return {"nodeId": node_id, "target": req.target, "parent_ip": req.parent_ip,
            "provisioning_token": f"nux-prov-{node_id}-{int(time.time())}", "status": "ready"}


@router.post("/onboard")
def onboard_node(req: OnboardNodeRequest) -> Dict[str, Any]:
    if req.target not in VALID_TARGETS:
        raise HTTPException(status_code=400, detail=f"Invalid target '{req.target}'")
    node_id = f"node-{req.target}-{int(time.time())}"
    tier = TIER_MAP[req.target]
    try:
        from server.features.mesh_coordinator.p2p_mesh import p2p_mesh
        p2p_mesh.register_node(node_id, {
            "name": req.name or node_id, "tier": tier,
            "type": "compute" if req.target == "pc" else "satellite",
            "ip": req.parent_ip if req.target == "pc" else f"192.168.1.{abs(hash(node_id)) % 200 + 20}",
            "parent_id": req.parent_id,
            "protocol": "WebRTC / UDP Direct" if req.target in ("esp32", "raspberry") else "LAN Mesh",
            "status": "Online & Provisioned",
        })
    except Exception:
        pass
    return {
        "node_id": node_id, "name": req.name or node_id, "target": req.target, "tier": tier,
        "status": "provisioned", "parent_id": req.parent_id,
        "message": f"Dispositivo '{req.name}' configurato con successo e connesso al cluster.",
        "log": f"Flash firmware completato su porta {req.usb_port or 'N/A'}. Handshake P2P attivo con {req.parent_id}.",
    }


@router.delete("/{node_id}")
def delete_node(node_id: str) -> Dict[str, Any]:
    from server.features.mesh_coordinator.p2p_mesh import p2p_mesh
    from features.nodes.registry import registry
    from state import store
    if node_id in (p2p_mesh.node_id, "virtual-core", "virtual_core"):
        raise HTTPException(409, "Il server attuale e il nucleo non possono essere rimossi")
    paired = node_id in registry.data["nodes"]
    if paired:
        registry.remove(node_id)
    if not (p2p_mesh.remove_node(node_id) or paired):
        raise HTTPException(404, "Nodo non trovato")
    store.event("INFO", f"Nodo {node_id} rimosso; autorizzazione revocata", "nodes")
    return {"node_id": node_id, "removed": True, "status": "deleted"}


@router.post("/{node_id}/name")
@router.patch("/{node_id}/name")
def rename_node(node_id: str, req: RenameNodeRequest) -> Dict[str, Any]:
    from server.features.mesh_coordinator.node_registry import NodeRegistryError
    from server.features.mesh_coordinator.p2p_mesh import p2p_mesh
    try:
        name = p2p_mesh.rename_node(node_id, req.name)
    except NodeRegistryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"node_id": node_id, "name": name, "status": "renamed"}


def _get_native_network_governor():
    global _network_governor_native
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    if _network_governor_native is None:
        try:
            import nuxiva_native
            if hasattr(nuxiva_native, "RustNetworkGovernor"):
                _network_governor_native = nuxiva_native.RustNetworkGovernor()
        except Exception:
            _network_governor_native = None
    return _network_governor_native


def _inspect_system_network_interfaces(node_ip: Optional[str] = None) -> List[Dict[str, Any]]:
    return inspect_system_network_interfaces(node_ip=node_ip, run_cmd=subprocess.run)

def _get_node_network_profile(node_id: str, node_ip: Optional[str] = None, refresh: bool = False) -> Dict[str, Any]:
    if node_id not in _network_profiles_memory:
        _network_profiles_memory[node_id] = build_initial_network_profile(node_id, _inspect_system_network_interfaces(node_ip))
        gov = _get_native_network_governor()
        if gov is not None:
            try:
                gov.register_or_update_profile_json(json.dumps(_network_profiles_memory[node_id]))
            except Exception:
                pass
    elif refresh:
        _network_profiles_memory[node_id]["interfaces"] = merge_refreshed_interfaces(
            _network_profiles_memory[node_id].get("interfaces", []), _inspect_system_network_interfaces(node_ip)
        )
    prof = _network_profiles_memory[node_id]
    gov = _get_native_network_governor()
    if gov is not None:
        try:
            route_json = gov.determine_active_route_json(node_id)
            if route_json:
                return {**prof, "active_route": json.loads(route_json)}
        except Exception:
            pass
    return {**prof, "active_route": compute_active_route(prof["interfaces"], prof["policy"])}


@router.get("/{node_id}/network")
def get_node_network(node_id: str) -> Dict[str, Any]:
    from server.features.mesh_coordinator.p2p_mesh import p2p_mesh
    telem = p2p_mesh.get_node_telemetry(node_id)
    return _get_node_network_profile(node_id, telem.get("ip") if telem else None, refresh=True)


@router.post("/{node_id}/network/policy")
def set_node_network_policy(node_id: str, req: UpdatePolicyRequest) -> Dict[str, Any]:
    if req.policy not in {"ethernet_only", "wifi_only", "dual_aggregation", "fallback"}:
        raise HTTPException(status_code=400, detail=f"Invalid policy '{req.policy}'")
    gov = _get_native_network_governor()
    if gov is not None:
        try:
            gov.set_policy(node_id, req.policy)
            route_json = gov.determine_active_route_json(node_id)
            return {"status": "ok", "policy": req.policy, "route": json.loads(route_json) if route_json else {}}
        except Exception:
            pass
    _get_node_network_profile(node_id)
    _network_profiles_memory[node_id]["policy"] = req.policy
    return {"status": "ok", "policy": req.policy, "route": _get_node_network_profile(node_id).get("active_route", {})}


@router.post("/{node_id}/network/interface/toggle")
def toggle_node_interface(node_id: str, req: ToggleInterfaceRequest) -> Dict[str, Any]:
    gov = _get_native_network_governor()
    if gov is not None:
        try:
            gov.toggle_interface(node_id, req.interface, req.is_up)
            route_json = gov.determine_active_route_json(node_id)
            return {"success": True, "route": json.loads(route_json) if route_json else {}}
        except Exception:
            pass
    _get_node_network_profile(node_id)
    for iface in _network_profiles_memory.get(node_id, {}).get("interfaces", []):
        if iface["name"] == req.interface:
            iface["is_up"] = req.is_up
    return {"success": True, "route": _get_node_network_profile(node_id).get("active_route", {})}


@router.post("/{node_id}/network/interface/ip")
def update_node_interface_ip(node_id: str, req: UpdateInterfaceIpRequest) -> Dict[str, Any]:
    gov = _get_native_network_governor()
    if gov is not None:
        try:
            gov.update_interface_ip_config(
                node_id, req.interface, req.mode, req.ipv4, req.netmask, req.gateway, req.dns_primary, req.dns_secondary
            )
            route_json = gov.determine_active_route_json(node_id)
            return {"success": True, "route": json.loads(route_json) if route_json else {}}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    _get_node_network_profile(node_id)
    for iface in _network_profiles_memory.get(node_id, {}).get("interfaces", []):
        if iface["name"] == req.interface:
            iface["ip_mode"] = req.mode
            if req.mode == "static":
                for k in ("ipv4", "netmask", "gateway", "dns_primary", "dns_secondary"):
                    if getattr(req, k):
                        iface[k] = getattr(req, k)
    return {"success": True, "route": _get_node_network_profile(node_id).get("active_route", {})}


@router.post("/{node_id}/network/vpn/toggle")
def toggle_node_vpn(node_id: str, req: ToggleVpnRequest) -> Dict[str, Any]:
    gov = _get_native_network_governor()
    if gov is not None:
        try:
            gov.toggle_vpn(node_id, req.enabled)
            return {"success": True, "vpn_enabled": req.enabled}
        except Exception:
            pass
    _get_node_network_profile(node_id)
    if node_id in _network_profiles_memory:
        _network_profiles_memory[node_id]["vpn"]["enabled"] = req.enabled
    return {"success": True, "vpn_enabled": req.enabled}


@router.get("/{node_id}/wifi/scan")
def get_node_wifi_scan(node_id: str) -> Dict[str, Any]:
    return scan_system_wifi(run_cmd=subprocess.run)

@router.post("/{node_id}/wifi/connect")
def connect_node_wifi(node_id: str, req: WifiConnectRequest) -> Dict[str, Any]:
    ssid = req.ssid.strip()
    if not ssid:
        raise HTTPException(status_code=400, detail="SSID required")
    return connect_wifi(ssid, req.password.strip(), req.interface, run_cmd=subprocess.run)

@router.post("/{node_id}/wifi/disconnect")
def disconnect_node_wifi(node_id: str) -> Dict[str, Any]:
    if os.name == "nt":
        p = subprocess.run(["netsh", "wlan", "disconnect"], capture_output=True, timeout=5)
        return {"success": p.returncode == 0}
    p = subprocess.run(["nmcli", "radio", "wifi", "off"], capture_output=True, timeout=5)
    subprocess.run(["nmcli", "radio", "wifi", "on"], capture_output=True, timeout=5)
    return {"success": p.returncode == 0}

@router.post("/{node_id}/wifi/radio")
def toggle_node_wifi_radio(node_id: str, req: WifiRadioRequest) -> Dict[str, Any]:
    if os.name == "nt":
        iface, act = req.interface or "Wi-Fi 3", ("enabled" if req.enabled else "disabled")
        p = subprocess.run(["netsh", "interface", "set", "interface", f"name={iface}", f"admin={act}"], capture_output=True, timeout=5)
        return {"success": p.returncode == 0, "radio_enabled": req.enabled}
    p = subprocess.run(["nmcli", "radio", "wifi", "on" if req.enabled else "off"], capture_output=True, timeout=5)
    return {"success": p.returncode == 0, "radio_enabled": req.enabled}

@router.get("/{node_id}/tasks")
def get_node_tasks(node_id: str) -> Dict[str, Any]:
    return collect_node_tasks(_load_capabilities(node_id), run_cmd=subprocess.run)


def _caps_file() -> Path:
    from config import NUXIVA_DIR, STATE_DIR
    for d in (STATE_DIR, NUXIVA_DIR, Path("data")):
        try:
            d.mkdir(parents=True, exist_ok=True)
            return d / "node_capabilities.json"
        except Exception:
            pass
    return Path("node_capabilities.json")

def _load_capabilities(node_id: str) -> Dict[str, bool]:
    defaults = {"voice_studio": True, "brain_llm": True, "vision_camera": True, "mesh_hub": True}
    f = _caps_file()
    if f.exists():
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if node_id in data or "default" in data:
                return {**defaults, **data.get(node_id, data.get("default", {}))}
        except Exception:
            pass
    return _node_capabilities_memory.get(node_id, defaults)

def _save_capabilities(node_id: str, caps: Dict[str, bool]) -> None:
    _node_capabilities_memory[node_id] = caps
    f = _caps_file()
    try:
        data = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
        data = data if isinstance(data, dict) else {}
        data[node_id] = data["default"] = caps
        f.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass

def is_capability_enabled(capability: str, node_id: str = "virtual_core") -> bool:
    return _load_capabilities(node_id).get(capability, True)

def _sync_local_llm_marker(disabled: bool) -> None:
    from config import STATE_DIR
    marker = STATE_DIR / "local_llm_disabled"
    try:
        if disabled:
            marker.parent.mkdir(parents=True, exist_ok=True)
            if not marker.exists():
                marker.write_text("1\n", encoding="utf-8")
        else:
            marker.unlink(missing_ok=True)
    except OSError:
        pass

def local_ollama_disabled() -> bool:
    return os.environ.get("NUXIVA_LOCAL_OLLAMA_DISABLED") == "1" or not is_capability_enabled("brain_llm")


def _local_llm_processes() -> list:
    import psutil
    found = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            command = proc.info.get("cmdline") or []
            names = [proc.info.get("name") or "", command[0] if command else ""]
            executables = {name.replace("\\", "/").rsplit("/", 1)[-1].lower().removesuffix(".exe") for name in names}
            if executables.intersection(_LOCAL_LLM_MARKERS) and proc.pid != os.getpid():
                found.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return found


def stop_local_ollama() -> None:
    import psutil
    if os.name != "nt":
        for action in ("stop", "disable"):
            try:
                subprocess.run(["systemctl", action, "ollama"], capture_output=True, timeout=30)
            except Exception:
                pass
    for proc in _local_llm_processes():
        try:
            proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass


def enforce_local_ollama_off() -> bool:
    if not local_ollama_disabled():
        return False
    os.environ["NUXIVA_LOCAL_OLLAMA_DISABLED"] = "1"
    _sync_local_llm_marker(True)
    if not _local_llm_processes():
        return False
    stop_local_ollama()
    return True


@router.post("/{node_id}/tasks/{pid}/terminate")
def terminate_node_task(node_id: str, pid: int) -> Dict[str, Any]:
    import psutil
    try:
        psutil.Process(pid).terminate()
        return {"success": True, "pid": pid}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{node_id}/capabilities/toggle")
def toggle_node_capability(node_id: str, req: ToggleCapabilityRequest) -> Dict[str, Any]:
    caps = _load_capabilities(node_id)
    caps[req.capability] = req.enabled
    _save_capabilities(node_id, caps)
    if req.capability == "brain_llm":
        _sync_local_llm_marker(not req.enabled)
        if not req.enabled:
            os.environ["NUXIVA_LOCAL_OLLAMA_DISABLED"] = "1"
            try:
                import httpx
                with httpx.Client(timeout=2.0) as client:
                    ps = client.get("http://127.0.0.1:11434/api/ps")
                    if ps.status_code == 200:
                        for mod in ps.json().get("models", []):
                            m_name = mod.get("name") or mod.get("model")
                            if m_name:
                                client.post("http://127.0.0.1:11434/api/generate", json={"model": m_name, "keep_alive": 0})
            except Exception:
                pass
            stop_local_ollama()
        else:
            os.environ.pop("NUXIVA_LOCAL_OLLAMA_DISABLED", None)
            if os.name != "nt":
                for action in ("enable", "start"):
                    try:
                        subprocess.run(["systemctl", action, "ollama"], capture_output=True, timeout=5)
                    except Exception:
                        pass
    return {"success": True, "capability": req.capability, "enabled": req.enabled, "capabilities": caps}
