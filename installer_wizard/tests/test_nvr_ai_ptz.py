import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from starlette.testclient import TestClient

from agenti.cameras.ptz import PtzController
from agenti.nvr import settings as nvr_settings
from agenti.nvr.analyzer import NvrAnalyzer
from agenti.nvr.api import admin_routes
from agenti.nvr.service import nvr
from agenti.nvr.store import EventStore
from agenti.nvr.vault import MediaVault


class NvrAiPtzTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.vault = MediaVault(continuous_seconds=60, event_seconds=3600)
        self.vault.root = self.root / "vault"
        self.vault.root.mkdir(parents=True, exist_ok=True)
        self.store = EventStore(self.root / "events.db")
        nvr._store = self.store
        from access import require_admin
        self.app = FastAPI()
        self.app.dependency_overrides[require_admin] = lambda: "admin"
        self.app.include_router(admin_routes)
        self.client = TestClient(self.app)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_settings_default_20_percent_quota(self):
        cfg = nvr_settings.load()
        self.assertEqual(cfg["storage_percent"], 20)
        self.assertEqual(cfg["record_mode"], "hybrid")
        self.assertTrue(cfg["ai_analysis"])
        self.assertTrue(cfg["ptz_auto_tracking"])

    def test_settings_validation_and_update(self):
        current = dict(nvr_settings.DEFAULTS)
        updated = nvr_settings.validate({"storage_percent": 30, "record_mode": "events", "ptz_auto_patrol": True}, current)
        self.assertEqual(updated["storage_percent"], 30)
        self.assertEqual(updated["record_mode"], "events")
        self.assertTrue(updated["ptz_auto_patrol"])

    def test_media_vault_storage_stats_and_quota(self):
        stats = self.vault.storage_stats(storage_percent=20)
        self.assertIn("disk_total_bytes", stats)
        self.assertIn("quota_bytes", stats)
        self.assertEqual(stats["storage_percent"], 20)
        self.assertEqual(stats["vault_segments"], 0)

    def test_media_vault_prune_quota(self):
        from agenti.nvr import archive as archive_mod
        store = archive_mod.NvrArchive(self.vault)
        with mock.patch.object(archive_mod, "probe", return_value={"duration_ms": 60000, "audio": True, "video": True}):
            for i in range(5):
                raw = self.root / f"seg_20261111_00{i}000.mp4"
                raw.write_bytes(b"DATA" * 1024)
                store.ingest("cam_test", raw)
        done = store.maintain([], {"continuous_hours": 48, "retention_days": 30, "storage_percent": 1,
                                   "storage_max_gb": 0.00001}, {}, now_ms=int(time.time() * 1000))
        self.assertGreater(done["evicted"], 0)
        self.assertLessEqual(done["kept_bytes"], 10737)

    def test_nvr_analyzer_description_and_details(self):
        analyzer = NvrAnalyzer()
        label, summary, details, score = analyzer.format_description(
            "front_door",
            [{"class": "person", "score": 0.9, "look": {"upper": "rossa", "lower": "blu", "carrying": ["pacco"]}}],
            ["buongiorno ho una consegna per lei"]
        )
        self.assertEqual(label, "person")
        self.assertIn("front_door", summary)
        self.assertIn("rossa", details)
        self.assertIn("buongiorno ho una consegna", details)
        self.assertGreaterEqual(score, 0.9)

    def test_nvr_event_store_add_search_and_get(self):
        ev = {
            "id": "ev_test_123",
            "at": time.time(),
            "camera": "cam_front",
            "label": "person",
            "score": 0.88,
            "source": "ai_analyzer",
            "zone": "entrance",
            "text": "Persona rilevata all'ingresso",
            "details": "Look: giacca rossa, pantaloni scuri. Audio: «ciao nuxiva»",
        }
        self.assertTrue(self.store.add(ev))
        fetched = self.store.get("ev_test_123")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["camera"], "cam_front")
        self.assertIn("giacca rossa", fetched["details"])

    def test_ptz_controller_capabilities_and_movement(self):
        ptz = PtzController()
        with mock.patch("agenti.cameras.cameras.cameras.items", {
            "cam_ip": {"id": "cam_ip", "name": "IP Camera PTZ", "kind": "onvif", "url": "rtsp://admin:pass@192.168.1.100:554/live"}
        }):
            caps = ptz.capabilities("cam_ip")
            self.assertTrue(caps["has_ptz"])
            self.assertTrue(caps["is_360"])
            res = ptz.move("cam_ip", 0.5, -0.2)
            self.assertTrue(res["ok"])
            preset_res = ptz.goto_preset("cam_ip", "home")
            self.assertTrue(preset_res["ok"])
            track_res = ptz.track("cam_ip", [0.1, 0.5, 0.2, 0.4])
            self.assertTrue(track_res["ok"])

    def test_api_storage_and_ptz(self):
        with mock.patch("agenti.nvr.api.require_admin", return_value="admin"), \
             mock.patch("agenti.nvr.api.media_vault", self.vault):
            res_storage = self.client.get("/api/nvr/storage")
            self.assertEqual(res_storage.status_code, 200)
            data = res_storage.json()
            self.assertEqual(data["storage_percent"], 20)

            res_ptz = self.client.get("/api/nvr/ptz/cameras")
            self.assertEqual(res_ptz.status_code, 200)

            res_ctrl = self.client.post("/api/nvr/ptz/control", json={"camera_id": "test", "action": "stop"})
            self.assertEqual(res_ctrl.status_code, 200)


if __name__ == "__main__":
    unittest.main()
