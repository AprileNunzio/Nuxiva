import threading
from typing import Any, Dict, List, Optional
from agenti.matter.bridge import MatterBridge
from agenti.matter.controller import MatterController
from agenti.matter.discovery import MatterDiscovery
from agenti.matter.model import MatterStandardVersion

class MatterCoordinator:
    _instance: Optional["MatterCoordinator"] = None
    _lock = threading.Lock()

    def __init__(self):
        self.bridge = MatterBridge()
        self.controller = MatterController()
        self.discovery = MatterDiscovery()
        self.spec_version = MatterStandardVersion.V1_6_1.value
        self.sync_system_devices()

    @classmethod
    def instance(cls) -> "MatterCoordinator":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def sync_system_devices(self) -> Dict[str, Any]:
        count = self.bridge.sync_system_entities()
        return {
            "status": "success",
            "bridged_entities_count": count,
            "total_endpoints": len(self.bridge.list_endpoints()),
        }

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

    def discover_network_devices(self, timeout: float = 1.5) -> List[Dict[str, Any]]:
        disc = MatterDiscovery(timeout=timeout)
        return disc.discover_commissionable()

    def auto_enroll_device(self, device_info: Dict[str, Any]) -> Dict[str, Any]:
        ip = str(device_info.get("ip") or "")
        disc = int(device_info.get("discriminator") or 3840)
        name = str(device_info.get("device_name") or f"Matter-{ip.replace('.', '')[-4:]}")
        dev_type = int(device_info.get("device_type") or 0x0100)
        pairing_code = f"AUTO-DISC-{disc:04d}-{ip}"
        node_res = self.commission_node(
            pairing_code=pairing_code,
            name=name,
            device_type=dev_type,
        )
        node_res["auto_enrolled"] = True
        node_res["source_ip"] = ip
        return node_res

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
        if node_id == 0 or node_id == self.bridge.node_id:
            return self.bridge.invoke_endpoint_command(
                endpoint_id=endpoint_id,
                cluster_id=cluster_id,
                command_id=command_id,
                payload=payload,
            )
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
