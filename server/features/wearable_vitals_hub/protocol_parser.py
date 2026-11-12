import math
import time
from typing import Any, Dict

from server.features.wearable_vitals_hub.interfaces import (
    BodyCompositionData, RealtimeVitalTelemetry, WearableProtocol,
)

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

MAX_BLE_FRAME_BYTES = 512
NATIVE_BLE = getattr(nuxiva_native, "vitals_parse_ble_heart_rate", None)


def number(data: Dict[str, Any], *keys: str):
    for key in keys:
        value = data.get(key)
        if value is None or isinstance(value, bool):
            continue
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(parsed):
            return parsed
    return None


class UniversalProtocolParser:
    def parse_ble_heart_rate_frame(self, device_id: str, raw_payload: bytes) -> RealtimeVitalTelemetry:
        result = RealtimeVitalTelemetry(device_id=device_id, device_name="BLE Heart Rate Monitor",
                                       protocol=WearableProtocol.BLE_STANDARD, timestamp=time.time())
        if not 2 <= len(raw_payload) <= MAX_BLE_FRAME_BYTES:
            return result
        if NATIVE_BLE is not None:
            result.heart_rate_bpm, result.hrv_rmssd_ms = NATIVE_BLE(bytes(raw_payload))
            return result
        flags = raw_payload[0]
        width = 2 if flags & 1 else 1
        if len(raw_payload) < 1 + width:
            return result
        bpm = int.from_bytes(raw_payload[1:1 + width], "little")
        if not 0 < bpm <= 250:
            return result
        result.heart_rate_bpm = float(bpm)
        index = 1 + width + (2 if flags & 8 else 0)
        intervals = []
        if flags & 16:
            while index + 2 <= len(raw_payload):
                interval = int.from_bytes(raw_payload[index:index + 2], "little") * 1000 / 1024
                if interval > 0:
                    intervals.append(interval)
                index += 2
        if len(intervals) >= 2:
            differences = [b - a for a, b in zip(intervals, intervals[1:])]
            rmssd = math.sqrt(sum(x * x for x in differences) / len(differences))
            if rmssd <= 300:
                result.hrv_rmssd_ms = rmssd
        elif len(intervals) == 1:
            result.hrv_rmssd_ms = min(300.0, max(5.0, intervals[0] * 0.08))
        return result

    def parse_fitbit_telemetry(self, device_id: str, data: Dict[str, Any]) -> RealtimeVitalTelemetry:
        return RealtimeVitalTelemetry(
            device_id=device_id, device_name=data.get("device_name") or "Fitbit",
            protocol=WearableProtocol.GOOGLE_FITBIT,
            heart_rate_bpm=number(data, "heart_rate", "bpm"),
            spo2_percentage=number(data, "spo2", "oxygen_saturation"),
            hrv_rmssd_ms=number(data, "hrv", "rmssd"),
            skin_temperature_celsius=number(data, "skin_temp"),
            electrodermal_activity_eda=number(data, "eda"),
            steps_today=number(data, "steps"), calories_burned_kcal=number(data, "calories"),
            respiratory_rate_rpm=number(data, "respiratory_rate"),
            battery_level_percentage=number(data, "battery"), timestamp=time.time())

    def parse_renpho_scale_data(self, device_id: str, data: Dict[str, Any]) -> BodyCompositionData:
        weight = number(data, "weight_kg", "weight")
        height = number(data, "height_m")
        bmi = number(data, "bmi")
        if bmi is None and weight is not None and height is not None and height > 0:
            bmi = round(weight / height ** 2, 2)
        return BodyCompositionData(
            device_id=device_id, timestamp=time.time(), weight_kg=weight, bmi=bmi,
            body_fat_percentage=number(data, "body_fat_percentage"),
            muscle_mass_kg=number(data, "muscle_mass_kg"), bone_mass_kg=number(data, "bone_mass_kg"),
            water_percentage=number(data, "water_percentage"),
            visceral_fat_index=number(data, "visceral_fat_index"),
            metabolic_age_years=number(data, "metabolic_age_years"))


protocol_parser = UniversalProtocolParser()
