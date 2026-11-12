import json
import os
import sys
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

sys.modules.setdefault("cv2", mock.MagicMock())

from fastapi.testclient import TestClient
from features.auto_update.self_healing import SelfHealingEngine
from features.auto_update.service import AutoUpdateService
import nuxiva_supervisor
import system_api
import setup_api


class TestAutoUpdateSelfHealing(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.state_dir = Path(self.tmp_dir.name) / "state"
        self.root_dir = Path(self.tmp_dir.name) / "root"
        self.state_dir.mkdir(parents=True)
        self.root_dir.mkdir(parents=True)
        self.engine = SelfHealingEngine(state_dir=self.state_dir, root_dir=self.root_dir)
        self.public_client = TestClient(nuxiva_supervisor.public)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_heal_activation_state_creates_when_setup_done(self):
        setup_file = self.state_dir / "setup.json"
        setup_file.write_text(json.dumps({"done": True}), encoding="utf-8")
        act_file = self.state_dir / "activation.json"
        self.assertFalse(act_file.exists())
        res = self.engine.heal_activation_state()
        self.assertTrue(res)
        self.assertTrue(act_file.exists())
        act_data = json.loads(act_file.read_text(encoding="utf-8"))
        self.assertEqual(act_data.get("stage"), "done")

    def test_heal_activation_state_skips_when_setup_not_done(self):
        setup_file = self.state_dir / "setup.json"
        setup_file.write_text(json.dumps({"done": False}), encoding="utf-8")
        act_file = self.state_dir / "activation.json"
        res = self.engine.heal_activation_state()
        self.assertTrue(res)
        self.assertFalse(act_file.exists())

    def test_heal_git_locks_removes_stale(self):
        git_dir = self.root_dir / ".git"
        git_dir.mkdir()
        lock_file = git_dir / "index.lock"
        lock_file.write_text("lock", encoding="utf-8")
        stale_time = time.time() - 300
        os.utime(lock_file, (stale_time, stale_time))
        res = self.engine.heal_git_locks()
        self.assertTrue(res)
        self.assertFalse(lock_file.exists())

    def test_activation_completed_returns_true_when_setup_done(self):
        with mock.patch.object(setup_api, "done", return_value=True):
            self.assertTrue(system_api._activation_completed())

    def test_activation_completed_returns_false_when_setup_not_done(self):
        with mock.patch.object(setup_api, "done", return_value=False):
            with mock.patch("config.STATE_DIR", self.state_dir):
                self.assertFalse(system_api._activation_completed())

    async def test_update_service_check_updates_graceful_error(self):
        service = AutoUpdateService()
        with mock.patch("updater.check", side_effect=RuntimeError("offline network")):
            with mock.patch("updater.current_rev", return_value="rev1234"):
                res = await service.check_updates(fresh=True)
                self.assertFalse(res["available"])
                self.assertIn("offline network", res["check_error"])
                self.assertEqual(res["local_rev"], "rev1234")

    def test_issue34_unblock_configured_system_serves_display(self):
        with mock.patch.object(setup_api, "done", return_value=True), \
             mock.patch.object(setup_api, "_private_client", return_value=True):
            res = self.public_client.get("/", follow_redirects=False)
            self.assertEqual(res.status_code, 200)
            self.assertIn("text/html", res.headers.get("content-type", ""))

    def test_auto_update_api_status_endpoint(self):
        with mock.patch("updater.current_rev", return_value="deadbeef1234"):
            res = self.public_client.get("/api/system/update/status")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["local_rev"], "deadbeef1234")
            self.assertIn("available", data)


if __name__ == "__main__":
    unittest.main()
