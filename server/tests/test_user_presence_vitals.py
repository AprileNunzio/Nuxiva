import unittest
import time
from server.features.user_presence_vitals.interfaces import (
    EmergencySeverity,
    EmergencyContact,
    EmergencyVitalsThresholds,
    UserHealthProfile,
)
from server.features.user_presence_vitals.emergency_detector import vitals_emergency_detector
from server.features.user_presence_vitals.presence_vitals_coordinator import presence_vitals_coordinator
from server.features.wearable_vitals_hub.interfaces import (
    RealtimeVitalTelemetry,
    WearableProtocol,
)

class UserPresenceVitalsEmergencyTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.profile = UserHealthProfile(
            user_id="test_user_emergency",
            full_name="Mario Rossi",
            associated_wearable_ids=["fitbit_edge_primary"],
            emergency_contacts=[
                EmergencyContact(
                    contact_id="cnt_01",
                    name="Laura Rossi",
                    relationship="Coniuge",
                    phone_number="+39 349 9988776",
                    notify_by_sms=True,
                    notify_by_call=True,
                    priority_order=1
                )
            ],
            thresholds=EmergencyVitalsThresholds(
                cardiac_arrest_min_bpm=28.0,
                extreme_tachycardia_max_bpm=185.0,
                hypoxia_critical_spo2=85.0
            )
        )

    def test_cardiac_arrest_detection(self):
        critical_vitals = RealtimeVitalTelemetry(
            device_id="fitbit_edge_primary",
            device_name="Google Fitbit Edge",
            protocol=WearableProtocol.GOOGLE_FITBIT,
            heart_rate_bpm=22.0,
            spo2_percentage=89.0,
            timestamp=time.time()
        )
        event = vitals_emergency_detector.evaluate_vitals(self.profile, critical_vitals)
        self.assertIsNotNone(event)
        self.assertEqual(event.severity, EmergencySeverity.FATAL_ARREST)
        self.assertIn("Arresto cardiaco", event.trigger_reason)

    def test_hypoxia_and_tachycardia_detection(self):
        hypoxia_vitals = RealtimeVitalTelemetry(
            device_id="fitbit_edge_primary",
            device_name="Google Fitbit Edge",
            protocol=WearableProtocol.GOOGLE_FITBIT,
            heart_rate_bpm=195.0,
            spo2_percentage=81.0,
            timestamp=time.time()
        )
        event = vitals_emergency_detector.evaluate_vitals(self.profile, hypoxia_vitals)
        self.assertIsNotNone(event)
        self.assertEqual(event.severity, EmergencySeverity.CRITICAL)
        self.assertIn("Tachicardia", event.trigger_reason)
        self.assertIn("Ipossia", event.trigger_reason)

    def test_normal_vitals_no_emergency(self):
        normal_vitals = RealtimeVitalTelemetry(
            device_id="fitbit_edge_primary",
            device_name="Google Fitbit Edge",
            protocol=WearableProtocol.GOOGLE_FITBIT,
            heart_rate_bpm=72.0,
            spo2_percentage=98.5,
            timestamp=time.time()
        )
        event = vitals_emergency_detector.evaluate_vitals(self.profile, normal_vitals)
        self.assertIsNone(event)

    async def test_approach_event_auto_connect_and_emergency_broadcast(self):
        presence_vitals_coordinator.register_or_update_profile(self.profile)

        critical_vitals = RealtimeVitalTelemetry(
            device_id="fitbit_edge_primary",
            device_name="Google Fitbit Edge",
            protocol=WearableProtocol.GOOGLE_FITBIT,
            heart_rate_bpm=24.0,
            spo2_percentage=82.0,
            timestamp=time.time()
        )
        res = await presence_vitals_coordinator.ingest_live_user_vitals("test_user_emergency", critical_vitals)
        self.assertTrue(res["emergency"] is not None)
        self.assertEqual(res["emergency"]["severity"], "fatal_arrest")
        self.assertEqual(res["broadcast"]["status"], "BROADCAST_COMPLETED")

if __name__ == "__main__":
    unittest.main()
