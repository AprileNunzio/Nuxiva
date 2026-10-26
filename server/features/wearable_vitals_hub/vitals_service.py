from typing import Optional
from server.features.wearable_vitals_hub.interfaces import (
    RealtimeVitalTelemetry,
    BodyCompositionData,
    WearableDeviceRegistration,
    WearableSystemState,
    ConnectionStatus,
)
from server.features.wearable_vitals_hub.device_registry import wearable_registry
from server.core.sensory_bus.event_router import sensory_bus
from server.core.event_sourcing.universal_space import UniversalObservation

class WearableVitalsService:
    def __init__(self):
        self._latest_vitals: Optional[RealtimeVitalTelemetry] = None
        self._latest_body_metrics: Optional[BodyCompositionData] = None
        # Real data only - no synthetic baseline

    async def ingest_vital_telemetry(self, vitals: RealtimeVitalTelemetry) -> RealtimeVitalTelemetry:
        self._latest_vitals = vitals
        wearable_registry.update_status(vitals.device_id, ConnectionStatus.CONNECTED)

        obs = UniversalObservation(
            modality="wearable_vitals",
            source_id=f"device:{vitals.device_id}",
            raw_data=vitals.model_dump(),
            metadata={
                "bpm": vitals.heart_rate_bpm,
                "spo2": vitals.spo2_percentage,
                "hrv": vitals.hrv_rmssd_ms,
                "timestamp": vitals.timestamp
            }
        )
        await sensory_bus.push_observation(obs)
        return vitals

    async def ingest_body_composition(self, data: BodyCompositionData) -> BodyCompositionData:
        self._latest_body_metrics = data
        wearable_registry.update_status(data.device_id, ConnectionStatus.CONNECTED)

        obs = UniversalObservation(
            modality="body_composition",
            source_id=f"device:{data.device_id}",
            raw_data=data.model_dump(),
            metadata={
                "weight_kg": data.weight_kg,
                "bmi": data.bmi,
                "timestamp": data.timestamp
            }
        )
        await sensory_bus.push_observation(obs)
        return data

    def get_system_state(self) -> WearableSystemState:
        devices = wearable_registry.list_devices()
        connected = sum(1 for d in devices if d.status == ConnectionStatus.CONNECTED)
        return WearableSystemState(
            connected_devices_count=connected,
            devices=devices,
            latest_vitals=self._latest_vitals,
            latest_body_metrics=self._latest_body_metrics,
            multimodal_fusion_active=True
        )

    def register_device(self, device: WearableDeviceRegistration) -> WearableDeviceRegistration:
        return wearable_registry.register_or_update(device)

wearable_vitals_service = WearableVitalsService()
