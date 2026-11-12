import time
from typing import Any, Dict, List, Optional
from agenti.matter.model import (
    MatterClusterId,
    MatterCommandId,
    MatterDeviceType,
    MatterNodeModel,
    MatterEndpointModel,
    MatterClusterModel,
    MatterAttributeModel,
)

class MatterController:
    def __init__(self):
        self._nodes: Dict[int, MatterNodeModel] = {}
        self._next_node_id = 0x1000

    def list_nodes(self) -> List[Dict[str, Any]]:
        return [
            {
                "node_id": node.node_id,
                "vendor_id": node.vendor_id,
                "product_id": node.product_id,
                "name": node.name,
                "version": node.version,
                "connected": node.connected,
                "endpoints": [
                    {
                        "id": ep.id,
                        "device_type": ep.device_type,
                        "name": ep.name,
                        "clusters": list(ep.clusters.keys()),
                    }
                    for ep in node.endpoints.values()
                ],
            }
            for node in self._nodes.values()
        ]

    def get_node(self, node_id: int) -> Optional[MatterNodeModel]:
        return self._nodes.get(node_id)

    def commission(
        self,
        pairing_code: str,
        name: Optional[str] = None,
        device_type: Optional[int] = None,
    ) -> Dict[str, Any]:
        node_id = self._next_node_id
        self._next_node_id += 1

        dev_type = device_type or MatterDeviceType.ON_OFF_LIGHT.value
        node_name = name or f"Matter-Node-{node_id:X}"

        ep1 = MatterEndpointModel(
            id=1,
            device_type=dev_type,
            name=node_name,
            clusters={},
        )

        if dev_type in (MatterDeviceType.ON_OFF_LIGHT.value, MatterDeviceType.ON_OFF_PLUG.value):
            ep1.clusters[MatterClusterId.ON_OFF.value] = MatterClusterModel(
                id=MatterClusterId.ON_OFF.value,
                name="OnOff",
                attributes={0x0000: MatterAttributeModel(0x0000, "OnOff", False, writable=True)},
                supported_commands=[MatterCommandId.OFF.value, MatterCommandId.ON.value, MatterCommandId.TOGGLE.value],
            )
        elif dev_type == MatterDeviceType.DIMMABLE_LIGHT.value:
            ep1.clusters[MatterClusterId.ON_OFF.value] = MatterClusterModel(
                id=MatterClusterId.ON_OFF.value,
                name="OnOff",
                attributes={0x0000: MatterAttributeModel(0x0000, "OnOff", False, writable=True)},
                supported_commands=[MatterCommandId.OFF.value, MatterCommandId.ON.value, MatterCommandId.TOGGLE.value],
            )
            ep1.clusters[MatterClusterId.LEVEL_CONTROL.value] = MatterClusterModel(
                id=MatterClusterId.LEVEL_CONTROL.value,
                name="LevelControl",
                attributes={0x0000: MatterAttributeModel(0x0000, "CurrentLevel", 254, writable=True)},
                supported_commands=[MatterCommandId.MOVE_TO_LEVEL.value],
            )
        elif dev_type == MatterDeviceType.THERMOSTAT.value:
            ep1.clusters[MatterClusterId.THERMOSTAT.value] = MatterClusterModel(
                id=MatterClusterId.THERMOSTAT.value,
                name="Thermostat",
                attributes={0x0000: MatterAttributeModel(0x0000, "LocalTemperature", 2150, writable=False)},
                supported_commands=[],
            )
        elif dev_type == MatterDeviceType.SECURITY_CAMERA.value:
            ep1.clusters[MatterClusterId.CAMERA_VIDEO_STREAM.value] = MatterClusterModel(
                id=MatterClusterId.CAMERA_VIDEO_STREAM.value,
                name="CameraVideoStream",
                attributes={0x0001: MatterAttributeModel(0x0001, "StreamActive", True, writable=False)},
                supported_commands=[],
            )
            ep1.clusters[MatterClusterId.PAN_TILT_ZOOM_CONTROL.value] = MatterClusterModel(
                id=MatterClusterId.PAN_TILT_ZOOM_CONTROL.value,
                name="PanTiltZoomControl",
                attributes={
                    0x0001: MatterAttributeModel(0x0001, "Pan", 0.0, writable=True),
                    0x0002: MatterAttributeModel(0x0002, "Tilt", 0.0, writable=True),
                    0x0003: MatterAttributeModel(0x0003, "Zoom", 1.0, writable=True),
                },
                supported_commands=[MatterCommandId.PTZ_MOVE.value, MatterCommandId.PTZ_STOP.value],
            )
        elif dev_type == MatterDeviceType.SMART_METER.value:
            ep1.clusters[MatterClusterId.ELECTRICAL_POWER_MEASUREMENT.value] = MatterClusterModel(
                id=MatterClusterId.ELECTRICAL_POWER_MEASUREMENT.value,
                name="ElectricalPowerMeasurement",
                attributes={0x0000: MatterAttributeModel(0x0000, "ActivePower", 340, writable=False)},
                supported_commands=[],
            )

        node = MatterNodeModel(
            node_id=node_id,
            vendor_id=0xFFF1,
            product_id=0x1234,
            name=node_name,
            version="1.6.1",
            connected=True,
            endpoints={1: ep1},
            metadata={"pairing_code": pairing_code, "commissioned_at": time.time()},
        )
        self._nodes[node_id] = node

        return {
            "status": "commissioned",
            "node_id": node_id,
            "name": node_name,
            "device_type": dev_type,
            "endpoints_count": len(node.endpoints),
        }

    def invoke_command(
        self,
        node_id: int,
        endpoint_id: int,
        cluster_id: int,
        command_id: int,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        node = self._nodes.get(node_id)
        if node is None:
            return {"status": "error", "message": "NodeNotFound"}

        ep = node.endpoints.get(endpoint_id)
        if ep is None:
            return {"status": "error", "message": "EndpointNotFound"}

        cl = ep.clusters.get(cluster_id)
        if cl is None:
            return {"status": "error", "message": "ClusterNotFound"}

        if command_id not in cl.supported_commands:
            return {"status": "error", "message": "CommandNotSupported"}

        payload = payload or {}

        if cluster_id == MatterClusterId.ON_OFF.value:
            attr = cl.attributes.get(0x0000)
            if attr is not None:
                if command_id == MatterCommandId.OFF.value:
                    attr.value = False
                elif command_id == MatterCommandId.ON.value:
                    attr.value = True
                elif command_id == MatterCommandId.TOGGLE.value:
                    attr.value = not bool(attr.value)
        elif cluster_id == MatterClusterId.LEVEL_CONTROL.value:
            attr = cl.attributes.get(0x0000)
            if attr is not None and "level" in payload:
                attr.value = int(payload["level"])
        elif cluster_id == MatterClusterId.PAN_TILT_ZOOM_CONTROL.value:
            if command_id == MatterCommandId.PTZ_MOVE.value:
                if "pan" in payload and 0x0001 in cl.attributes:
                    cl.attributes[0x0001].value = float(payload["pan"])
                if "tilt" in payload and 0x0002 in cl.attributes:
                    cl.attributes[0x0002].value = float(payload["tilt"])
                if "zoom" in payload and 0x0003 in cl.attributes:
                    cl.attributes[0x0003].value = float(payload["zoom"])

        return {
            "status": "success",
            "node_id": node_id,
            "endpoint_id": endpoint_id,
            "cluster_id": cluster_id,
            "command_id": command_id,
        }
