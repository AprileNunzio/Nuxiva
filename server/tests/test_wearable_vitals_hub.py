import unittest
import time
from server.features.wearable_vitals_hub.interfaces import (
    BodyCompositionData,
    WearableProtocol,
    RealtimeVitalTelemetry,
)
from server.features.wearable_vitals_hub.protocol_parser import protocol_parser
from server.features.wearable_vitals_hub.vitals_service import wearable_vitals_service

class WearableVitalsHubTest(unittest.IsolatedAsyncioTestCase):
    def test_protocol_parser_fitbit_edge(self):
        fitbit_data = {
            "device_name": "Google Fitbit Edge",
            "heart_rate": 74.0,
            "spo2": 99.2,
            "hrv": 52.0,
            "skin_temp": 36.7,
            "eda": 0.04,
            "steps": 10540,
            "calories": 2450.0,
            "respiratory_rate": 14.0,
            "battery": 92
        }
        vitals = protocol_parser.parse_fitbit_telemetry("fitbit_edge_test", fitbit_data)
        self.assertEqual(vitals.device_id, "fitbit_edge_test")
        self.assertEqual(vitals.heart_rate_bpm, 74.0)
        self.assertEqual(vitals.spo2_percentage, 99.2)
        self.assertEqual(vitals.steps_today, 10540)
        self.assertEqual(vitals.battery_level_percentage, 92)

    def test_protocol_parser_ble_heart_rate(self):
        raw_ble_bytes = bytes([0x10, 0x48, 0x10, 0x02])
        telemetry = protocol_parser.parse_ble_heart_rate_frame("ble_band_01", raw_ble_bytes)
        self.assertEqual(telemetry.heart_rate_bpm, 72.0)
        self.assertIsNotNone(telemetry.hrv_rmssd_ms)

    def test_protocol_parser_renpho_smart_scale(self):
        scale_payload = {
            "weight_kg": 73.8,
            "height_m": 1.78,
            "body_fat_percentage": 15.2,
            "muscle_mass_kg": 35.8,
            "water_percentage": 60.1,
            "bone_mass_kg": 3.3,
            "visceral_fat_index": 4,
            "metabolic_age_years": 26
        }
        metrics = protocol_parser.parse_renpho_scale_data("renpho_scale_test", scale_payload)
        self.assertEqual(metrics.weight_kg, 73.8)
        self.assertEqual(metrics.bmi, 23.29)
        self.assertEqual(metrics.body_fat_percentage, 15.2)
        self.assertEqual(metrics.visceral_fat_index, 4)

    async def test_vitals_service_ingest_and_state(self):
        vitals = RealtimeVitalTelemetry(
            device_id="fitbit_edge_primary",
            device_name="Google Fitbit Edge",
            protocol=WearableProtocol.GOOGLE_FITBIT,
            heart_rate_bpm=66.0,
            spo2_percentage=98.8,
            hrv_rmssd_ms=54.0,
            timestamp=time.time()
        )
        ingested = await wearable_vitals_service.ingest_vital_telemetry(vitals)
        self.assertEqual(ingested.heart_rate_bpm, 66.0)

        body_data = BodyCompositionData(
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
        await wearable_vitals_service.ingest_body_composition(body_data)
        state = wearable_vitals_service.get_system_state()
        self.assertGreaterEqual(state.connected_devices_count, 1)
        self.assertIsNotNone(state.latest_vitals)
        self.assertIsNotNone(state.latest_body_metrics)

if __name__ == "__main__":
    unittest.main()
