import unittest
from unittest import mock

from fastapi.testclient import TestClient

import nuxiva_supervisor
from agenti.agency import proactive


class AgencyProactiveTest(unittest.TestCase):
    def test_sample_telemetry_returns_valid_metrics(self):
        telem = proactive.sample_telemetry()
        self.assertGreater(telem.cpu_count, 0)
        self.assertGreaterEqual(telem.disk_total_gb, 0.0)
        self.assertGreaterEqual(telem.disk_free_gb, 0.0)
        self.assertGreaterEqual(telem.disk_used_percent, 0.0)
        self.assertEqual(len(telem.load_avg), 3)

    def test_insights_triggers_disk_warning_when_pressure_high(self):
        telem = proactive.TelemetrySnapshot(
            timestamp=100.0,
            cpu_count=4,
            load_avg=(1.0, 1.0, 1.0),
            disk_total_gb=100.0,
            disk_free_gb=5.0,
            disk_used_percent=95.0,
        )
        insights = proactive.analyze_insights([], [], telem)
        ids = [i.id for i in insights]
        self.assertIn("ins_disk_pressure", ids)

    def test_insights_triggers_open_questions_warning(self):
        telem = proactive.sample_telemetry()
        questions = [{"id": "q1", "status": "open", "prompt": "Scelta cloud?"}]
        insights = proactive.analyze_insights([], questions, telem)
        ids = [i.id for i in insights]
        self.assertIn("ins_blocked_questions", ids)

    def test_insights_healthy_default(self):
        telem = proactive.TelemetrySnapshot(
            timestamp=100.0,
            cpu_count=4,
            load_avg=(0.1, 0.1, 0.1),
            disk_total_gb=100.0,
            disk_free_gb=50.0,
            disk_used_percent=50.0,
        )
        insights = proactive.analyze_insights([], [], telem)
        ids = [i.id for i in insights]
        self.assertIn("ins_healthy", ids)

    def test_generate_briefing_italian(self):
        insights = [proactive.ProactiveInsight("1", "alert", "Disco", "Disco quasi pieno.", "clean", "critical")]
        counts = {"total": 10, "done": 7, "running": 2, "review": 1}
        briefing = proactive.generate_briefing("it", "E-commerce", counts, insights)
        self.assertIn("NunzioTech Agency", briefing)
        self.assertIn("70%", briefing)
        self.assertIn("Attenzione", briefing)

    def test_generate_briefing_english(self):
        insights = []
        counts = {"total": 5, "done": 5, "running": 0, "review": 0}
        briefing = proactive.generate_briefing("en", "Core Engine", counts, insights, user_name="Sarah")
        self.assertIn("Sarah", briefing)
        self.assertIn("NunzioTech Agency", briefing)
        self.assertIn("100%", briefing)
        self.assertIn("optimally", briefing)


class AgencyBriefingApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.web = TestClient(nuxiva_supervisor.public)

    def test_briefing_endpoint(self):
        fake_detail = {
            "project": {"id": "proj-1", "title": "Piattaforma Web", "questions": []},
            "tasks": [
                {"id": "t1", "title": "Setup", "status": "done"},
                {"id": "t2", "title": "API", "status": "running"},
            ],
            "counts": {"total": 2, "done": 1, "running": 1, "review": 0},
        }
        with mock.patch("agenti.agency.api.require_display", lambda r: None), \
             mock.patch("agenti.agency.service.detail", mock.AsyncMock(return_value=fake_detail)):
            res = self.web.get("/api/agency/board/proj-1/briefing", headers={"X-Nuxiva-Request": "1"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["project_id"], "proj-1")
        self.assertIn("NunzioTech Agency", data["briefing"])
        self.assertIsInstance(data["insights"], list)
        self.assertIn("cpu_count", data["telemetry"])
