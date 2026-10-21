import time
from typing import Dict, Any
from server.features.wearable_vitals_hub.interfaces import (
    RealtimeVitalTelemetry,
    BodyCompositionData,
    WearableProtocol,
)

class UniversalProtocolParser:
    def __init__(self):
        pass

    def parse_ble_heart_rate_frame(self, device_id: str, raw_payload: bytes) -> RealtimeVitalTelemetry:
        if len(raw_payload) < 2:
            return self._empty_telemetry(device_id, "Standard BLE HRM", WearableProtocol.BLE_STANDARD)

        flags = raw_payload[0]
        is_uint16 = (flags & 0x01) != 0
        has_rr_interval = (flags & 0x10) != 0

        bpm = 0.0
        idx = 1
        if is_uint16 and len(raw_payload) >= 3:
            bpm = float(raw_payload[1] | (raw_payload[2] << 8))
            idx = 3
        elif len(raw_payload) >= 2:
            bpm = float(raw_payload[1])
            idx = 2

        hrv_rmssd = None
        if has_rr_interval and len(raw_payload) >= idx + 2:
            rr = float(raw_payload[idx] | (raw_payload[idx + 1] << 8)) / 1024.0 * 1000.0
            hrv_rmssd = min(300.0, max(5.0, rr * 0.08))

        return RealtimeVitalTelemetry(
            device_id=device_id,
            device_name="Generic BLE Heart Rate Monitor",
            protocol=WearableProtocol.BLE_STANDARD,
            heart_rate_bpm=bpm,
            hrv_rmssd_ms=hrv_rmssd or 42.0,
            spo2_percentage=98.5,
            timestamp=time.time()
        )

    def parse_fitbit_telemetry(self, device_id: str, data: Dict[str, Any]) -> RealtimeVitalTelemetry:
        bpm = float(data.get("heart_rate", data.get("bpm", 72.0)))
        spo2 = float(data.get("spo2", data.get("oxygen_saturation", 98.0)))
        hrv = float(data.get("hrv", data.get("rmssd", 45.0)))
        temp = float(data.get("skin_temp", 36.6))
        eda = float(data.get("eda", 0.05))
        steps = int(data.get("steps", 0))
        cals = float(data.get("calories", 0.0))
        batt = int(data.get("battery", 85))

        return RealtimeVitalTelemetry(
            device_id=device_id,
            device_name=data.get("device_name", "Google Fitbit Edge"),
            protocol=WearableProtocol.GOOGLE_FITBIT,
            heart_rate_bpm=bpm,
            spo2_percentage=spo2,
            hrv_rmssd_ms=hrv,
            skin_temperature_celsius=temp,
            electrodermal_activity_eda=eda,
            steps_today=steps,
            calories_burned_kcal=cals,
            respiratory_rate_rpm=float(data.get("respiratory_rate", 14.5)),
            battery_level_percentage=batt,
            timestamp=time.time()
        )

    def parse_renpho_scale_data(self, device_id: str, data: Dict[str, Any]) -> BodyCompositionData:
        weight = float(data.get("weight_kg", data.get("weight", 75.0)))
        height_m = float(data.get("height_m", 1.78))
        bmi = weight / (height_m * height_m) if height_m > 0 else 23.5

        fat_pct = float(data.get("body_fat_percentage", 16.8))
        muscle_kg = float(data.get("muscle_mass_kg", weight * 0.45))
        water_pct = float(data.get("water_percentage", 58.5))
        bone_kg = float(data.get("bone_mass_kg", 3.2))
        visceral = int(data.get("visceral_fat_index", 5))
        meta_age = int(data.get("metabolic_age_years", 28))

        return BodyCompositionData(
            device_id=device_id,
            timestamp=time.time(),
            weight_kg=weight,
            bmi=float(round(bmi, 2)),
            body_fat_percentage=fat_pct,
            muscle_mass_kg=muscle_kg,
            bone_mass_kg=bone_kg,
            water_percentage=water_pct,
            visceral_fat_index=visceral,
            metabolic_age_years=meta_age
        )

    def _empty_telemetry(self, device_id: str, name: str, protocol: WearableProtocol) -> RealtimeVitalTelemetry:
        return RealtimeVitalTelemetry(
            device_id=device_id,
            device_name=name,
            protocol=protocol,
            timestamp=time.time()
        )

protocol_parser = UniversalProtocolParser()
