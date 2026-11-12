import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from starlette.testclient import TestClient

from access import require_admin
from features.sentinel import recalibrate
from features.sentinel.api import admin_routes


class SentinelRecalibrateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        os.environ["NUXIVA_STATE_ROOT"] = str(self.root)
        os.environ["NUXIVA_EAR_REVIEW_DIR"] = str(self.root / "ear_review")
        recalibrate.STATE_FILE = self.root / "sentinel_recalibrate.json"

        self.app = FastAPI()
        self.app.dependency_overrides[require_admin] = lambda: "admin"
        self.app.include_router(admin_routes)
        self.client = TestClient(self.app)

    def tearDown(self):
        os.environ.pop("NUXIVA_EAR_REVIEW_DIR", None)
        self.tmp.cleanup()

    def test_collect_metrics_default(self):
        metrics = recalibrate.collect_metrics()
        self.assertEqual(metrics["precision"], 1.0)
        self.assertEqual(metrics["ok_count"], 0)
        self.assertEqual(metrics["wrong_count"], 0)
        self.assertIn("voice_match_threshold", metrics["parameters"])

    def test_collect_metrics_with_feedback(self):
        fake_journal = mock.MagicMock()
        fake_journal.ready = True
        fake_journal.entries.return_value = [
            {"verdict": "ok"},
            {"verdict": "ok"},
            {"verdict": "wrong"},
        ]
        with mock.patch("features.ear.journal.journal", fake_journal):
            metrics = recalibrate.collect_metrics()
            self.assertEqual(metrics["ok_count"], 2)
            self.assertEqual(metrics["wrong_count"], 1)
            self.assertAlmostEqual(metrics["precision"], 0.667, places=2)

    def test_run_cycle_adjusts_parameters_on_low_precision(self):
        fake_journal = mock.MagicMock()
        fake_journal.ready = True
        fake_journal.entries.return_value = [
            {"verdict": "ok"},
            {"verdict": "wrong"},
            {"verdict": "wrong"},
            {"verdict": "wrong"},
        ]
        with mock.patch("features.ear.journal.journal", fake_journal):
            res = recalibrate.run_cycle()
            self.assertLess(res["precision"], 0.75)
            self.assertGreater(res["parameters"]["voice_match_threshold"], 0.62)
            self.assertGreater(res["parameters"]["voice_margin"], 0.06)
            self.assertGreater(res["parameters"]["gait_threshold"], 0.60)
            self.assertTrue(len(res["agency_tasks"]) > 0)

    def test_run_cycle_parameters_respect_bounds(self):
        fake_journal = mock.MagicMock()
        fake_journal.ready = True
        fake_journal.entries.return_value = [{"verdict": "wrong"}] * 20
        with mock.patch("features.ear.journal.journal", fake_journal):
            for _ in range(25):
                res = recalibrate.run_cycle()
            self.assertLessEqual(res["parameters"]["voice_match_threshold"], recalibrate.VOICE_THRESH_BOUNDS[1])
            self.assertLessEqual(res["parameters"]["voice_margin"], recalibrate.VOICE_MARGIN_BOUNDS[1])
            self.assertLessEqual(res["parameters"]["gait_threshold"], recalibrate.GAIT_THRESH_BOUNDS[1])

    def test_recalibrate_api_endpoints(self):
        res_get = self.client.get("/api/sentinel/recalibrate/metrics")
        self.assertEqual(res_get.status_code, 200)
        self.assertIn("precision", res_get.json())

        res_post = self.client.post("/api/sentinel/recalibrate/run")
        self.assertEqual(res_post.status_code, 200)
        self.assertIn("parameters", res_post.json())
        self.assertIn("agency_tasks", res_post.json())
