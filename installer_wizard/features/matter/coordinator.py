import threading
from typing import Any, Dict, List, Optional
from features.matter.bridge import MatterBridge
from features.matter.controller import MatterController
from features.matter.model import MatterStandardVersion

class MatterCoordinator:
    _instance: Optional["MatterCoordinator"] = None
    _lock = threading.Lock()

    def __init__(self):
        self.bridge = MatterBridge()
        self.controller = MatterController()
        self.spec_version = MatterStandardVersion.V1_6_1.value
        self._sync_default_entities()

    @classmethod
    def instance(cls) -> "MatterCoordinator":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _sync_default_entities(self) -> None:
        self.bridge.bridge_entity("light.main", "on_off_light", "Luce Principale")
        self.bridge.bridge_entity("sensor.living_presence", "occupancy_sensor", "Presenza Salotto")
        self.bridge.bridge_entity("camera.ptz_360", "security_camera_ptz", "Telecamera 360° PTZ")
        self.bridge.bridge_entity("alarm.home_rescue", "smoke_co_alarm", "Allarme Soccorso")
        self.bridge.bridge_entity("meter.main_grid", "smart_energy_meter", "Contatore Rete")

    def get_status(self) -> Dict[str, Any]:
        return {
            "spec": self.spec_version,
            "standard": "Matter 1.6.1 (CSA)",
            "controller_nodes_count": len(self.controller.list_nodes()),
            "bridge_endpoints_count": len(self.bridge.list_endpoints()),
            "bridge_active": True,
        }

    def list_nodes(self) -> List[Dict[str, Any]]:
        return self.controller.list_nodes()

    def commission_node(
        self,
        pairing_code: str,
        name: Optional[str] = None,
        device_type: Optional[int] = None,
    ) -> Dict[str, Any]:
        return self.controller.commission(pairing_code, name=name, device_type=device_type)

    def invoke_node_command(
        self,
        node_id: int,
        endpoint_id: int,
        cluster_id: int,
        command_id: int,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self.controller.invoke_command(
            node_id=node_id,
            endpoint_id=endpoint_id,
            cluster_id=cluster_id,
            command_id=command_id,
            payload=payload,
        )

    def list_bridge_endpoints(self) -> List[Dict[str, Any]]:
        return self.bridge.list_endpoints()

    def update_bridge_state(
        self,
        entity_id: str,
        cluster_id: int,
        attr_id: int,
        value: Any,
    ) -> bool:
        return self.bridge.update_state(entity_id, cluster_id, attr_id, value)
