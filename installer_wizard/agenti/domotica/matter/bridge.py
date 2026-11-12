import json
from typing import Any, Dict, List, Optional
from agenti.matter.model import (
    MatterClusterId,
    MatterCommandId,
    MatterDeviceType,
)

class MatterBridge:
    def __init__(self, node_id: int = 0x1122334455667788, vendor_id: int = 0xFFF1, product_id: int = 0x8001):
        self.node_id = node_id
        self.vendor_id = vendor_id
        self.product_id = product_id
        self._endpoints: Dict[int, Dict[str, Any]] = {}
        self._entity_map: Dict[str, int] = {}
        self._next_ep_id = 1
        self._rust_bridge = None

        try:
            from features.native_core import symbol
            rust_cls = symbol("RustMatterBridge")
            if rust_cls is not None:
                self._rust_bridge = rust_cls(node_id, vendor_id, product_id)
        except Exception:
            self._rust_bridge = None

        self._setup_root()

    def _setup_root(self) -> None:
        self._endpoints[0] = {
            "id": 0,
            "device_type": MatterDeviceType.ROOT_NODE.value,
            "name": "Root",
            "clusters": {
                MatterClusterId.BASIC_INFORMATION.value: {
                    "id": MatterClusterId.BASIC_INFORMATION.value,
                    "name": "BasicInformation",
                    "attributes": {
                        0x0001: "Nuxiva",
                        0x0002: self.vendor_id,
                        0x0003: "Nuxiva Universal Bridge 1.6.1",
                        0x0004: self.product_id,
                    },
                }
            },
        }

    def bridge_entity(self, entity_id: str, kind: str, label: str) -> int:
        if entity_id in self._entity_map:
            return self._entity_map[entity_id]

        ep_id = self._next_ep_id
        self._next_ep_id += 1

        if self._rust_bridge is not None:
            try:
                self._rust_bridge.bridge_entity(entity_id, kind, label)
            except Exception:
                pass

        dev_type = MatterDeviceType.BRIDGED_NODE.value
        clusters: Dict[int, Dict[str, Any]] = {}

        if kind in ("on_off_light", "light"):
            dev_type = MatterDeviceType.ON_OFF_LIGHT.value
            clusters[MatterClusterId.ON_OFF.value] = {
                "id": MatterClusterId.ON_OFF.value,
                "name": "OnOff",
                "attributes": {0x0000: False},
                "commands": [MatterCommandId.OFF.value, MatterCommandId.ON.value, MatterCommandId.TOGGLE.value],
            }
        elif kind in ("dimmable_light",):
            dev_type = MatterDeviceType.DIMMABLE_LIGHT.value
            clusters[MatterClusterId.ON_OFF.value] = {
                "id": MatterClusterId.ON_OFF.value,
                "name": "OnOff",
                "attributes": {0x0000: False},
                "commands": [MatterCommandId.OFF.value, MatterCommandId.ON.value, MatterCommandId.TOGGLE.value],
            }
            clusters[MatterClusterId.LEVEL_CONTROL.value] = {
                "id": MatterClusterId.LEVEL_CONTROL.value,
                "name": "LevelControl",
                "attributes": {0x0000: 254},
                "commands": [MatterCommandId.MOVE_TO_LEVEL.value],
            }
        elif kind in ("thermostat", "climate"):
            dev_type = MatterDeviceType.THERMOSTAT.value
            clusters[MatterClusterId.THERMOSTAT.value] = {
                "id": MatterClusterId.THERMOSTAT.value,
                "name": "Thermostat",
                "attributes": {0x0000: 2100},
            }
        elif kind in ("temperature_sensor", "sensor_temp"):
            dev_type = MatterDeviceType.TEMPERATURE_SENSOR.value
            clusters[MatterClusterId.TEMPERATURE_MEASUREMENT.value] = {
                "id": MatterClusterId.TEMPERATURE_MEASUREMENT.value,
                "name": "TemperatureMeasurement",
                "attributes": {0x0000: 2050},
            }
        elif kind in ("occupancy_sensor", "presence"):
            dev_type = MatterDeviceType.OCCUPANCY_SENSOR.value
            clusters[MatterClusterId.OCCUPANCY_SENSING.value] = {
                "id": MatterClusterId.OCCUPANCY_SENSING.value,
                "name": "OccupancySensing",
                "attributes": {0x0000: 0},
            }
        elif kind in ("contact_sensor", "door"):
            dev_type = MatterDeviceType.CONTACT_SENSOR.value
            clusters[MatterClusterId.BOOLEAN_STATE.value] = {
                "id": MatterClusterId.BOOLEAN_STATE.value,
                "name": "BooleanState",
                "attributes": {0x0000: False},
            }
        elif kind in ("smoke_co_alarm", "rescue_alarm"):
            dev_type = MatterDeviceType.SMOKE_CO_ALARM.value
            clusters[MatterClusterId.SMOKE_CO_ALARM.value] = {
                "id": MatterClusterId.SMOKE_CO_ALARM.value,
                "name": "SmokeCOAlarm",
                "attributes": {0x0000: 0},
                "commands": [MatterCommandId.EMERGENCY_ALARM.value, MatterCommandId.SILENCE_ALARM.value],
            }
        elif kind in ("security_camera_ptz", "camera"):
            dev_type = MatterDeviceType.SECURITY_CAMERA.value
            clusters[MatterClusterId.CAMERA_VIDEO_STREAM.value] = {
                "id": MatterClusterId.CAMERA_VIDEO_STREAM.value,
                "name": "CameraVideoStream",
                "attributes": {0x0001: True},
            }
            clusters[MatterClusterId.PAN_TILT_ZOOM_CONTROL.value] = {
                "id": MatterClusterId.PAN_TILT_ZOOM_CONTROL.value,
                "name": "PanTiltZoomControl",
                "attributes": {0x0001: 0.0, 0x0002: 0.0, 0x0003: 1.0},
                "commands": [MatterCommandId.PTZ_MOVE.value, MatterCommandId.PTZ_STOP.value],
            }
        elif kind in ("smart_energy_meter", "energy"):
            dev_type = MatterDeviceType.SMART_METER.value
            clusters[MatterClusterId.ELECTRICAL_POWER_MEASUREMENT.value] = {
                "id": MatterClusterId.ELECTRICAL_POWER_MEASUREMENT.value,
                "name": "ElectricalPowerMeasurement",
                "attributes": {0x0000: 0},
            }
            clusters[MatterClusterId.ELECTRICAL_ENERGY_MEASUREMENT.value] = {
                "id": MatterClusterId.ELECTRICAL_ENERGY_MEASUREMENT.value,
                "name": "ElectricalEnergyMeasurement",
                "attributes": {0x0001: 0},
            }

        self._endpoints[ep_id] = {
            "id": ep_id,
            "entity_id": entity_id,
            "device_type": dev_type,
            "name": label,
            "clusters": clusters,
        }
        self._entity_map[entity_id] = ep_id
        return ep_id

    def update_state(self, entity_id: str, cluster_id: int, attr_id: int, value: Any) -> bool:
        ep_id = self._entity_map.get(entity_id)
        if ep_id is None or ep_id not in self._endpoints:
            return False

        if self._rust_bridge is not None:
            try:
                val_json = json.dumps(value)
                self._rust_bridge.update_entity_state(entity_id, cluster_id, attr_id, val_json)
            except Exception:
                pass

        ep = self._endpoints[ep_id]
        if cluster_id in ep["clusters"]:
            ep["clusters"][cluster_id]["attributes"][attr_id] = value
            return True
        return False

    def invoke_endpoint_command(
        self,
        endpoint_id: int,
        cluster_id: int,
        command_id: int,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        ep = self._endpoints.get(endpoint_id)
        if ep is None:
            return {"status": "error", "message": "EndpointNotFound"}

        entity_id = str(ep.get("entity_id") or "")
        cl = ep.get("clusters", {}).get(cluster_id)
        if cl is None:
            return {"status": "error", "message": "ClusterNotFound"}

        if cluster_id == MatterClusterId.PAN_TILT_ZOOM_CONTROL.value:
            cam_id = entity_id.replace("camera.", "")
            params = payload or {}
            pan = float(params.get("pan", 0.0))
            tilt = float(params.get("tilt", 0.0))
            zoom = float(params.get("zoom", 0.0))
            if command_id == MatterCommandId.PTZ_MOVE.value:
                try:
                    from agenti.cameras.ptz import PtzController
                    PtzController().move(cam_id, pan, tilt, zoom)
                except Exception:
                    pass
                self.update_state(entity_id, cluster_id, 0x0001, pan)
                self.update_state(entity_id, cluster_id, 0x0002, tilt)
                self.update_state(entity_id, cluster_id, 0x0003, zoom)
                return {"status": "success", "cluster": "PanTiltZoomControl", "pan": pan, "tilt": tilt, "zoom": zoom}
            elif command_id == MatterCommandId.PTZ_STOP.value:
                try:
                    from agenti.cameras.ptz import PtzController
                    PtzController().move(cam_id, 0.0, 0.0, 0.0)
                except Exception:
                    pass
                return {"status": "success", "cluster": "PanTiltZoomControl", "action": "stopped"}

        if cluster_id == MatterClusterId.ON_OFF.value:
            current = bool(cl.get("attributes", {}).get(0x0000, False))
            target = not current if command_id == MatterCommandId.TOGGLE.value else (command_id == MatterCommandId.ON.value)
            self.update_state(entity_id, cluster_id, 0x0000, target)
            return {"status": "success", "cluster": "OnOff", "value": target}

        return {"status": "success", "command_id": command_id}

    def sync_system_entities(self) -> int:
        count = 0
        try:
            from agenti.cameras.cameras import cameras
            for cid, cam in cameras.items.items():
                cam_name = cam.get("name") or f"Camera {cid}"
                self.bridge_entity(f"camera.{cid}", "security_camera_ptz", cam_name)
                count += 1
        except Exception:
            pass

        try:
            from agenti.home_assistant.home import HomeBrain
            hb = HomeBrain()
            for eid, ent in getattr(hb, "entities", {}).items():
                domain = eid.split(".")[0]
                label = ent.get("name") or eid
                if domain in ("light", "switch"):
                    self.bridge_entity(eid, "on_off_light", label)
                    count += 1
                elif domain in ("sensor", "binary_sensor"):
                    self.bridge_entity(eid, "occupancy_sensor", label)
                    count += 1
                elif domain == "climate":
                    self.bridge_entity(eid, "thermostat", label)
                    count += 1
        except Exception:
            pass

        return count

    def read_attribute(self, endpoint_id: int, cluster_id: int, attr_id: int) -> Optional[Any]:
        ep = self._endpoints.get(endpoint_id)
        if ep is None:
            return None
        cl = ep.get("clusters", {}).get(cluster_id)
        if cl is None:
            return None
        return cl.get("attributes", {}).get(attr_id)

    def list_endpoints(self) -> List[Dict[str, Any]]:
        return list(self._endpoints.values())

    def get_endpoint_by_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        ep_id = self._entity_map.get(entity_id)
        if ep_id is not None:
            return self._endpoints.get(ep_id)
        return None
