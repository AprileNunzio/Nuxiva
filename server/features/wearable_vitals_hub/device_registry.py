import time
from typing import Dict, List, Optional
from server.features.wearable_vitals_hub.interfaces import (
    WearableDeviceRegistration,
    WearableProtocol,
    ConnectionStatus,
)

class WearableDeviceRegistry:
    def __init__(self):
        self._devices: Dict[str, WearableDeviceRegistration] = {}
        self._initialize_default_catalog()

    def register_or_update(self, device: WearableDeviceRegistration) -> WearableDeviceRegistration:
        device.last_sync_timestamp = time.time()
        self._devices[device.device_id] = device
        return device

    def get_device(self, device_id: str) -> Optional[WearableDeviceRegistration]:
        return self._devices.get(device_id)

    def list_devices(self) -> List[WearableDeviceRegistration]:
        return list(self._devices.values())

    def update_status(self, device_id: str, status: ConnectionStatus) -> bool:
        dev = self._devices.get(device_id)
        if not dev:
            return False
        dev.status = status
        dev.last_sync_timestamp = time.time()
        return True

    def remove_device(self, device_id: str) -> bool:
        if device_id in self._devices:
            del self._devices[device_id]
            return True
        return False

    def _initialize_default_catalog(self):
        fitbit = WearableDeviceRegistration(
            device_id="fitbit_edge_primary",
            name="Google Fitbit Edge (Nunzio)",
            protocol=WearableProtocol.GOOGLE_FITBIT,
            mac_address="E4:5F:01:2A:9C:14",
            is_active=True,
            status=ConnectionStatus.CONNECTED,
            last_sync_timestamp=time.time()
        )
        renpho = WearableDeviceRegistration(
            device_id="renpho_scale_01",
            name="Renpho Smart Body Composition Scale",
            protocol=WearableProtocol.RENPHO_SMART_SCALE,
            mac_address="C8:FD:19:B3:04:77",
            is_active=True,
            status=ConnectionStatus.CONNECTED,
            last_sync_timestamp=time.time()
        )
        self._devices[fitbit.device_id] = fitbit
        self._devices[renpho.device_id] = renpho

wearable_registry = WearableDeviceRegistry()
