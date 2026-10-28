import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import feature_registry
from config import read_env, write_env
from feature_registry import Registry
from packages import step_wanted
from state import store
from steps import run_pipeline


class KioskToggleTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)
        self.test_env = self.tmp_path / "nuxiva.env"
        self.test_env.write_text("NUXIVA_KIOSK=1\n", encoding="utf-8")
        self.env_patch = patch("config.ENV_FILE", self.test_env)
        self.env_patch.start()
        store.steps.clear()
        store.steps["kiosk"] = {"status": "done", "progress": 100}

    def tearDown(self):
        self.env_patch.stop()
        self._tmp.cleanup()

    def test_kiosk_toggle_persistence_and_wanted(self):
        state_file = self.tmp_path / "features.json"
        with patch.object(feature_registry, "STATE_FILE", state_file):
            registry = Registry()
            registry.scan()
            self.assertIsNotNone(registry.features.get("kiosk"))

            write_env({"NUXIVA_KIOSK": "0"})
            registry.note_env_change({"NUXIVA_KIOSK": "0"})
            self.assertEqual(registry._rec("kiosk")["mode"], "0")
            self.assertFalse(registry.enabled("kiosk"))

            registry2 = Registry()
            registry2.scan()
            self.assertEqual(registry2._rec("kiosk")["mode"], "0")
            self.assertFalse(registry2.enabled("kiosk"))

            env = read_env()
            self.assertEqual(env.get("NUXIVA_KIOSK"), "0")
            self.assertFalse(step_wanted("kiosk", env))

    async def test_kiosk_pipeline_teardown_status(self):
        with patch.dict("os.environ", {"NUXIVA_TEST_AUTH": "1"}):
            write_env({"NUXIVA_KIOSK": "0"})
            store.steps["kiosk"] = {"status": "done", "progress": 100}
            mock_action = AsyncMock(return_value=(0, ""))
            with patch("steps.run_step_action", mock_action):
                ok = await run_pipeline(only=["kiosk"], force=True)
                self.assertTrue(ok)
                self.assertEqual(store.steps["kiosk"]["status"], "disabled")
