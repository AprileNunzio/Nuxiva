import time
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
        self._initialize_baseline_metrics()

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

    def _initialize_baseline_metrics(self):
        self._latest_vitals = RealtimeVitalTelemetry(
            device_id="fitbit_edge_primary",
            device_name="Google Fitbit Edge (Nunzio)",
            protocol=wearable_registry.get_device("fitbit_edge_primary").protocol,
            heart_rate_bpm=68.0,
            spo2_percentage=99.0,
            hrv_rmssd_ms=48.2,
            skin_temperature_celsius=36.5,
            electrodermal_activity_eda=0.03,
            steps_today=8420,
            calories_burned_kcal=2140.0,
            respiratory_rate_rpm=13.5,
            battery_level_percentage=88,
            timestamp=time.time()
        )
        self._latest_body_metrics = BodyCompositionData(
            device_id="renpho_scale_01",
            timestamp=time.time(),
            weight_kg=74.6,
            bmi=23.4,
            body_fat_percentage=15.8,
            muscle_mass_kg=35.2,
            bone_mass_kg=3.3,
            water_percentage=59.4,
            visceral_fat_index=4,
            metabolic_age_years=27
        )

wearable_vitals_service = WearableVitalsService()
