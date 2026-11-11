import unittest
from unittest import mock

from fastapi import FastAPI
from starlette.testclient import TestClient

from access import require_admin
from features.rescue.api import admin_routes
from features.rescue.coordinator import RescueCoordinator
from features.rescue.detector import detect_speech_intent, detect_visual_distress


class RescueEmergencyTest(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.dependency_overrides[require_admin] = lambda: "admin"
        self.app.include_router(admin_routes)
        self.client = TestClient(self.app)

    def test_detect_speech_intent_multilingual(self):
        kind, score = detect_speech_intent("Aiuto, sono caduto e sto male!")
        self.assertEqual(kind, "help_words")
        self.assertGreaterEqual(score, 0.9)

        kind, score = detect_speech_intent("Help me, I fell and I cannot get up!")
        self.assertEqual(kind, "help_words")

        kind, score = detect_speech_intent("Socorro, me caí y no me puedo levantar")
        self.assertEqual(kind, "help_words")

        kind, score = detect_speech_intent("Au secours, je suis tombé et je ne peux pas me lever")
        self.assertEqual(kind, "help_words")

        kind, score = detect_speech_intent("Attenzione al fuoco in cucina!")
        self.assertEqual(kind, "fire")

        kind, score = detect_speech_intent("Fire! The room is on fire!")
        self.assertEqual(kind, "fire")

        kind, score = detect_speech_intent("Tranquillo sto bene, tutto a posto")
        self.assertEqual(kind, "all_clear")

        kind, score = detect_speech_intent("I am fine, false alarm, all good")
        self.assertEqual(kind, "all_clear")

        kind, score = detect_speech_intent("Je vais bien, fausse alerte")
        self.assertEqual(kind, "all_clear")

        kind, score = detect_speech_intent("Che bel tempo oggi per fare una passeggiata")
        self.assertIsNone(kind)
        self.assertEqual(score, 0.0)

    def test_detect_visual_distress_heuristics(self):
        kind, score, _ = detect_visual_distress([{"class": "fall", "score": 0.88}])
        self.assertEqual(kind, "fall")
        self.assertEqual(score, 0.88)

        kind, score, _ = detect_visual_distress([{"class": "immobility", "score": 0.72}])
        self.assertEqual(kind, "immobility")
        self.assertEqual(score, 0.72)

        kind, score, _ = detect_visual_distress([
            {"class": "person", "score": 0.85, "bbox": [100, 200, 320, 150]}
        ])
        self.assertEqual(kind, "fall")

        kind, score, _ = detect_visual_distress([
            {"class": "person", "score": 0.9, "bbox": [100, 50, 100, 300]}
        ])
        self.assertIsNone(kind)

    @mock.patch("features.sentinel.record.record")
    def test_coordinator_fall_and_escalation_flow(self, mock_record):
        coord = RescueCoordinator(prefer_native=False)
        step = coord.observe("fall", 0.9, 0.8, "cam_living", at=0.0, now=0.0)
        self.assertEqual(step["stage"], "watching")

        step = coord.observe("immobility", 0.9, 0.8, "cam_living", at=1.0, now=1.0)
        self.assertEqual(step["stage"], "check_in")
        self.assertTrue(any(a["type"] == "ask_person" for a in step["actions"]))
        mock_record.assert_called()

        step = coord.update(now=35.0)
        self.assertEqual(step["stage"], "alerting")
        self.assertTrue(any(a["type"] == "alert_family" for a in step["actions"]))

        step = coord.update(now=160.0)
        self.assertEqual(step["stage"], "alerting")
        self.assertTrue(any(a["type"] == "alert_family" for a in step["actions"]))

        step = coord.update(now=280.0)
        self.assertEqual(step["stage"], "emergency")
        self.assertTrue(any(a["type"] == "alert_emergency_contacts" for a in step["actions"]))

    @mock.patch("features.sentinel.record.record")
    def test_coordinator_person_ok_recovery(self, mock_record):
        coord = RescueCoordinator(prefer_native=False)
        coord.need_help(now=0.0)
        status = coord.status()
        self.assertIn(status["stage"], ("alerting", "emergency"))

        step = coord.person_ok(now=5.0)
        self.assertEqual(step["stage"], "cooldown")
        self.assertTrue(any(a["type"] == "stand_down" for a in step["actions"]))

    @mock.patch("features.redalert.service.RedAlert.trigger")
    @mock.patch("features.redalert.service.RedAlert.stop")
    def test_coordinator_home_alarm_on_fire(self, mock_stop, mock_trigger):
        coord = RescueCoordinator(prefer_native=False)
        step = coord.observe("smoke", 0.95, 1.0, "smoke_kitchen", at=0.0, now=0.0)
        self.assertTrue(any(a["type"] == "home_alarm" for a in step["actions"]))
        mock_trigger.assert_called()

        coord.dismiss(now=2.0)
        mock_stop.assert_called()

    def test_rescue_api_endpoints(self):
        resp = self.client.get("/api/rescue/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("stage", data)
        self.assertIn("timeline", data)
        self.assertIn("policy", data)

        resp = self.client.post("/api/rescue/observe", json={
            "kind": "help_words",
            "probability": 0.9,
            "confidence": 0.85,
            "source": "mic_bedroom",
            "now": 10.0
        })
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["ok"])

        resp = self.client.post("/api/rescue/respond", json={"action": "person_ok", "now": 15.0})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])

        resp = self.client.get("/api/rescue/policy")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("check_in_s", resp.json())

        resp = self.client.post("/api/rescue/policy", json={"check_in_s": 25.0})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["policy"]["check_in_s"], 25.0)
