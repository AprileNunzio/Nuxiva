import socket
import json
import threading
import logging
import time
from typing import Any, Dict, Optional

try:
    from .gpu_probe import gpu_probe
    from .node_registry import NodeRegistry
except ImportError:
    from gpu_probe import gpu_probe
    from node_registry import NodeRegistry

log = logging.getLogger("nuxiva.mesh")

VIRTUAL_CORE_ID = "virtual-core"

try:
    from nuxiva_native import RustCrdtMesh, RustP2PStreamManager
except ImportError:
    RustCrdtMesh = None
    RustP2PStreamManager = None


def collect_real_system_telemetry(node_id: Optional[str] = None) -> Dict[str, Any]:
    hostname = socket.gethostname()
    actual_id = node_id or hostname

    # Real primary IP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        real_ip = s.getsockname()[0]
    except Exception:
        real_ip = '127.0.0.1'
    finally:
        s.close()

    cpu_percent = 0.0
    cpu_cores = 1
    cpu_name = None
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=None)
        cpu_cores = psutil.cpu_count(logical=True) or 1
        mem = psutil.virtual_memory()
        ram_used_gb = round(mem.used / (1024**3), 2)
        ram_total_gb = round(mem.total / (1024**3), 2)
    except Exception:
        ram_used_gb = 0.0
        ram_total_gb = 1.0

    import platform
    os_info = f"{platform.system()} {platform.machine()}"
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if "model name" in line:
                    cpu_name = line.split(":", 1)[1].strip()
                    break
    except Exception:
        cpu_name = platform.processor() or f"CPU {cpu_cores} Cores"

    temp_c = None
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp_c = round(int(f.read().strip()) / 1000.0, 1)
    except Exception:
        pass

    tx_kbps = 0.0
    rx_kbps = 0.0
    try:
        import psutil
        net = psutil.net_io_counters()
        tx_kbps = round(net.bytes_sent / 1024.0, 1)
        rx_kbps = round(net.bytes_recv / 1024.0, 1)
    except Exception:
        pass

    gpu = gpu_probe.summary()
    return {
        "node_id": actual_id,
        "name": hostname,
        "tier": "Tier-1 (Compute & Virtual Core)",
        "ip": real_ip,
        "os": os_info,
        "cpu_percent": cpu_percent,
        "cpu_name": cpu_name,
        "cpu_cores": cpu_cores,
        "ram_used_gb": ram_used_gb,
        "ram_total_gb": ram_total_gb,
        "gpu_name": gpu["gpu_name"],
        "gpu_count": gpu["gpu_count"],
        "gpus": gpu["gpus"],
        "vram_used_gb": gpu["vram_used_gb"],
        "vram_total_gb": gpu["vram_total_gb"],
        "active_model": None,
        "power_watts": gpu["gpu_power_watts"],
        "temp_c": temp_c,
        "ping_ms": 0.1,
        "tx_kbps": tx_kbps,
        "rx_kbps": rx_kbps,
        "child_satellites": [],
        "status": "Attivo (Host Reale)",
        "is_remote_vpn": False,
        "last_updated": time.time()
    }


def _cpu_cores() -> int:
    import os
    return os.cpu_count() or 1


def _load() -> float:
    import os
    try:
        return round(os.getloadavg()[0] / _cpu_cores(), 3)
    except (AttributeError, OSError):
        return 0.0


class NuxivaMeshCoordinator:
    """
    Nuxiva Mesh OS v5.0 — Coordinatore P2P Decentralizzato.
    Implementa:
    1. Sincronizzazione CRDT del Control Plane del Nucleo Virtuale (condiviso tra tutti i PC).
    2. Protocollo Direct P2P Streaming (Satellite -> IP Nodo Padre diretto, 0% carico su altri nodi).
    3. Telemetria real-time ad alta frequenza (2Hz) per l'HUD Spaziale.
    """
    def __init__(self, port: int = 9999, node_id: Optional[str] = None):
        self.node_id = node_id or socket.gethostname()
        self.port = port
        self.peers: Dict[str, Dict[str, Any]] = {}
        self.running = False
        self.sock: Optional[socket.socket] = None

        # CRDT State Ledger
        self._crdt = RustCrdtMesh() if RustCrdtMesh is not None else None
        self._py_crdt: Dict[str, Dict[str, Any]] = {}

        # Direct P2P Stream Manager
        self._stream_mgr = RustP2PStreamManager() if RustP2PStreamManager is not None else None
        self._bindings: Dict[str, Dict[str, Any]] = {}

        # Telemetry State for all known nodes
        self.telemetry_store: Dict[str, Dict[str, Any]] = {}
        self.registry = NodeRegistry()
        self._restore_bindings()

    def _restore_bindings(self) -> None:
        for node_id, binding in self.registry.bindings().items():
            self._apply_binding(
                node_id,
                binding.get("satellite_ip", "0.0.0.0"),
                binding.get("parent_node_id", VIRTUAL_CORE_ID),
                binding.get("parent_ip", "127.0.0.1"),
                binding.get("stream_type", "audio_pcm"),
            )

    def display_name(self, node_id: str, fallback: Optional[str] = None) -> str:
        return self.registry.custom_name(node_id) or fallback or node_id

    @property
    def crdt(self):
        """Accesso diretto all'istanza RustCrdtMesh."""
        return self._crdt

    def start_discovery(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock.bind(("", self.port))
            self.running = True
            threading.Thread(target=self._listen_for_peers, daemon=True).start()
            threading.Thread(target=self._broadcast_presence, daemon=True).start()
            log.info(f"Nuxiva Mesh v5.0 attivato. Node ID: {self.node_id}. Porta: {self.port}")
        except Exception as exc:
            log.warning(f"Impossibile avviare socket broadcast mesh: {exc}")

    def stop_discovery(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass

    def _listen_for_peers(self):
        while self.running and self.sock:
            try:
                data, addr = self.sock.recvfrom(65535)
                msg = json.loads(data.decode('utf-8'))
                sender_id = msg.get("node_id")
                action = msg.get("action")

                if sender_id and sender_id != self.node_id:
                    if action == "HELLO":
                        self.peers[sender_id] = {
                            **self.peers.get(sender_id, {}),
                            "ip": addr[0],
                            "capabilities": msg.get("capabilities", {}),
                            "load": msg.get("load", 0.0),
                            "last_seen": time.time()
                        }
                    elif action == "CRDT_SYNC":
                        remote_crdt = msg.get("crdt_payload", "{}")
                        self.merge_crdt_state(remote_crdt)
                    elif action == "TELEMETRY":
                        telem = msg.get("telemetry", {})
                        if telem:
                            self.telemetry_store[sender_id] = telem
            except Exception:
                pass

    def _broadcast_presence(self):
        while self.running and self.sock:
            try:
                payload = {
                    "node_id": self.node_id,
                    "action": "HELLO",
                    "capabilities": {"gpus": gpu_probe.summary()["gpu_count"], "cpu_cores": _cpu_cores()},
                    "load": _load(),
                    "timestamp": time.time()
                }
                msg = json.dumps(payload).encode('utf-8')
                self.sock.sendto(msg, ("<broadcast>", self.port))
            except Exception:
                pass
            time.sleep(5)

    # ---------------- CRDT VIRTUAL CORE REPLICATION ----------------
    def set_crdt_setting(self, key: str, value: Any) -> bool:
        ts_ms = int(time.time() * 1000)
        val_str = json.dumps(value) if not isinstance(value, str) else value
        if self._crdt is not None:
            res = self._crdt.set(key, val_str, ts_ms, self.node_id)
        else:
            self._py_crdt[key] = {"value": val_str, "timestamp_ms": ts_ms, "node_id": self.node_id}
            res = True
        return res

    def get_crdt_setting(self, key: str) -> Optional[Any]:
        if self._crdt is not None:
            val_str = self._crdt.get(key)
        else:
            entry = self._py_crdt.get(key)
            val_str = entry["value"] if entry else None

        if val_str is None:
            return None
        try:
            return json.loads(val_str)
        except Exception:
            return val_str

    def export_crdt_state(self) -> str:
        if self._crdt is not None:
            return self._crdt.to_json()
        return json.dumps(self._py_crdt)

    def merge_crdt_state(self, remote_json: str) -> int:
        if self._crdt is not None:
            return self._crdt.merge_json(remote_json)
        try:
            remote = json.loads(remote_json)
            updated = 0
            for k, v in remote.items():
                local = self._py_crdt.get(k)
                if local is None or v.get("timestamp_ms", 0) > local.get("timestamp_ms", 0):
                    self._py_crdt[k] = v
                    updated += 1
            return updated
        except Exception:
            return 0

    # ---------------- DIRECT P2P STREAMING (SATELLITE -> PARENT) ----------------
    def bind_satellite_to_parent(
        self,
        satellite_id: str,
        satellite_ip: str,
        parent_node_id: str,
        parent_ip: str,
        stream_type: str = "audio"
    ) -> None:
        self._apply_binding(satellite_id, satellite_ip, parent_node_id, parent_ip, stream_type)
        self.registry.set_binding(satellite_id, {
            "parent_node_id": parent_node_id,
            "parent_ip": parent_ip,
            "satellite_ip": satellite_ip,
            "stream_type": stream_type,
        })

    def _apply_binding(
        self,
        satellite_id: str,
        satellite_ip: str,
        parent_node_id: str,
        parent_ip: str,
        stream_type: str,
    ) -> None:
        if self._stream_mgr is not None:
            self._stream_mgr.register_binding(
                satellite_id, satellite_ip, parent_node_id, parent_ip, stream_type
            )
        self._bindings[satellite_id] = {
            "satellite_id": satellite_id,
            "satellite_ip": satellite_ip,
            "parent_node_id": parent_node_id,
            "parent_ip": parent_ip,
            "stream_type": stream_type,
            "active": True,
            "bytes_transferred": 0
        }
        log.info(
            f"P2P Direct Stream configurato: Satellite {satellite_id} ({satellite_ip}) -> "
            f"Parent {parent_node_id} ({parent_ip}) via {stream_type}"
        )

    def resolve_stream_destination(self, satellite_id: str) -> Optional[str]:
        """Ritorna l'IP diretto del Nodo Padre designato (Zero-Hop)."""
        if self._stream_mgr is not None:
            target = self._stream_mgr.resolve_direct_target(satellite_id)
            if target:
                return target
        b = self._bindings.get(satellite_id)
        if b and b.get("active"):
            return b.get("parent_ip")
        return None

    def record_direct_stream_traffic(self, satellite_id: str, byte_count: int) -> bool:
        """Traccia il traffico diretto (100% offload su nodo padre, 0% su nodi terzi)."""
        if self._stream_mgr is not None:
            self._stream_mgr.record_transfer(satellite_id, byte_count)
        if satellite_id in self._bindings:
            self._bindings[satellite_id]["bytes_transferred"] += byte_count
            return True
        return False

    def register_node(self, node_id: str, peer_info: Dict[str, Any], telemetry: Optional[Dict[str, Any]] = None) -> None:
        """Registra esplicitamente un nodo onboardato nel cluster mesh."""
        self.peers[node_id] = peer_info
        if telemetry:
            self.telemetry_store[node_id] = telemetry
        else:
            self.telemetry_store[node_id] = {
                "node_id": node_id,
                "name": peer_info.get("name", node_id),
                "ip": peer_info.get("ip", "127.0.0.1"),
                "tier": peer_info.get("tier", "Tier-2 Satellite"),
                "status": "Connesso via P2P Mesh",
                "last_updated": time.time(),
            }

    def remove_node(self, node_id: str) -> bool:
        """Rimuove un nodo dal cluster mesh e revoca i suoi binding di stream."""
        removed = False
        if node_id in self.peers:
            del self.peers[node_id]
            removed = True
        if node_id in self.telemetry_store:
            del self.telemetry_store[node_id]
            removed = True
        if node_id in self._bindings:
            del self._bindings[node_id]
        self.registry.forget(node_id)
        return removed

    def rename_node(self, node_id: str, new_name: str) -> str:
        return self.registry.set_custom_name(node_id, new_name)

    # ---------------- LIVE HOVER TELEMETRY (2Hz STREAM) ----------------
    def get_node_telemetry(self, node_id: str) -> Dict[str, Any]:
        """Ritorna la telemetria real-time del nodo specificato (senza dati inventati)."""
        source = self.telemetry_store.get(node_id) or collect_real_system_telemetry(node_id)
        telemetry = dict(source)
        telemetry["name"] = self.display_name(node_id, source.get("name"))
        return telemetry

    def resolve_parent(
        self, node_id: str, default_parent: Optional[str], known_ids: Optional[set] = None
    ) -> Optional[str]:
        binding = self._bindings.get(node_id)
        if not binding or not binding.get("active"):
            return default_parent
        parent = binding.get("parent_node_id")
        if parent == VIRTUAL_CORE_ID:
            return None
        known = known_ids if known_ids is not None else {self.node_id, *self.peers.keys()}
        return parent if parent in known and parent != node_id else default_parent

    def get_mesh_canvas_state(self) -> Dict[str, Any]:
        """
        Ritorna lo stato topologico per il Mesh Topology Canvas:
        Nessun nodo inventato, solo host reale e satelliti effettivamente connessi.
        """
        local_telem = self.get_node_telemetry(self.node_id)
        local_id = self.node_id

        nodes = [
            {
                "id": local_id,
                "name": local_telem.get("name", local_id),
                "tier": "Tier-1 (Compute & Virtual Core)",
                "type": "compute",
                "ip": local_telem.get("ip", "127.0.0.1"),
                "status": "Host Locale Attivo",
                "x": 0,
                "y": 0,
                "telemetry": local_telem
            }
        ]
        links = []

        # Aggiunge SOLO i nodi satelliti/peer reali che hanno effettuato handshake
        for peer_id, peer_info in self.peers.items():
            peer_telem = self.telemetry_store.get(peer_id, {})
            p_ip = peer_info.get("ip", peer_telem.get("ip", "0.0.0.0"))
            p_name = self.display_name(peer_id, peer_info.get("name") or peer_telem.get("name"))
            p_tier = peer_info.get("tier", "Tier-2 (Smart Edge Satellite)")
            p_parent = self.resolve_parent(peer_id, local_id)
            nodes.append({
                "id": peer_id,
                "name": p_name,
                "tier": p_tier,
                "type": peer_info.get("type", "satellite"),
                "ip": p_ip,
                "parent_id": p_parent,
                "is_remote_vpn": peer_info.get("is_remote_vpn", False),
                "telemetry": {**peer_telem, "name": p_name} if peer_telem else {
                    "node_id": peer_id,
                    "name": p_name,
                    "ip": p_ip,
                    "tier": p_tier,
                    "status": "Connesso via P2P Mesh",
                    "last_updated": time.time()
                }
            })
            links.append({
                "source": p_parent or VIRTUAL_CORE_ID,
                "target": peer_id,
                "protocol": peer_info.get("protocol", "P2P Stream")
            })

        return {"nodes": nodes, "links": links, "timestamp": time.time()}


p2p_mesh = NuxivaMeshCoordinator()
