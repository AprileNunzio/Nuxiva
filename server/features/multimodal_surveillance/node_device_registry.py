import time
from typing import Dict, List, Optional
from server.features.multimodal_surveillance.interfaces import (
    SatelliteNodeConfig,
    NodeRole,
)

class NodeDeviceRegistry:
    def __init__(self):
        self._nodes: Dict[str, SatelliteNodeConfig] = {}
        self._initialize_default_nodes()

    def register_or_update_node(self, config: SatelliteNodeConfig) -> SatelliteNodeConfig:
        config.last_heartbeat = time.time()
        self._nodes[config.node_id] = config
        return config

    def get_node(self, node_id: str) -> Optional[SatelliteNodeConfig]:
        return self._nodes.get(node_id)

    def list_nodes(self) -> List[SatelliteNodeConfig]:
        return list(self._nodes.values())

    def update_heartbeat(self, node_id: str) -> bool:
        node = self._nodes.get(node_id)
        if not node:
            return False
        node.last_heartbeat = time.time()
        node.is_active = True
        return True

    def auto_configure_satellite(
        self,
        node_id: str,
        name: str,
        endpoint_url: str,
        detected_camera: Optional[str] = None,
        detected_mic: Optional[str] = None,
        detected_audio_out: Optional[str] = None,
        psk: Optional[str] = None
    ) -> SatelliteNodeConfig:
        existing = self._nodes.get(node_id)
        cam = detected_camera or (existing.default_camera_id if existing else f"cam_{node_id}_01")
        mic = detected_mic or (existing.default_microphone_id if existing else f"mic_{node_id}_01")
        out = detected_audio_out or (existing.default_audio_output_id if existing else f"spk_{node_id}_01")
        key = psk or (existing.psk_key if existing else "psk_zero_latency_secured_hash_99")

        config = SatelliteNodeConfig(
            node_id=node_id,
            name=name,
            role=NodeRole.SATELLITE,
            endpoint_url=endpoint_url,
            default_camera_id=cam,
            default_microphone_id=mic,
            default_audio_output_id=out,
            psk_key=key,
            is_active=True,
            last_heartbeat=time.time()
        )
        self._nodes[node_id] = config
        return config

    def _initialize_default_nodes(self):
        master = SatelliteNodeConfig(
            node_id="master_server",
            name="Server Principale Nuxiva",
            role=NodeRole.MASTER,
            endpoint_url="http://127.0.0.1:8000",
            default_camera_id="cam_main_entrance",
            default_microphone_id="mic_desk_array",
            default_audio_output_id="spk_monitor_stereo",
            psk_key="psk_master_secure_token_root_2026",
            is_active=True
        )
        sat1 = SatelliteNodeConfig(
            node_id="satellite_gate",
            name="Satellite Cancello & Perimetro",
            role=NodeRole.SATELLITE,
            endpoint_url="http://192.168.1.120:9000",
            default_camera_id="cam_gate_4k_outdoor",
            default_microphone_id="mic_intercom_gate",
            default_audio_output_id="spk_gate_horn",
            psk_key="psk_satellite_gate_token_2026",
            is_active=True
        )
        self._nodes[master.node_id] = master
        self._nodes[sat1.node_id] = sat1

node_device_registry = NodeDeviceRegistry()
