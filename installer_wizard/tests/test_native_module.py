import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import native_module


class BuildStatusTests(unittest.TestCase):

    def setUp(self):
        self.file = Path(tempfile.mkdtemp()) / "build.json"
        patcher = mock.patch.object(native_module, "BUILD_FILE", self.file)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_missing_file_is_unknown(self):
        self.assertEqual(native_module.build_status()["state"], "unknown")

    def test_states_and_stages_are_whitelisted(self):
        self.file.write_text(json.dumps({"state": "building", "stage": "wheel", "at": 1.5, "message": "<b>x</b>"}), encoding="utf-8")
        self.assertEqual(native_module.build_status(), {"state": "building", "stage": "wheel", "at": 1.5})
        self.file.write_text(json.dumps({"state": "evil", "stage": "../x", "at": "now"}), encoding="utf-8")
        self.assertEqual(native_module.build_status(), {"state": "unknown", "stage": None, "at": None})
        self.file.write_text("{broken", encoding="utf-8")
        with self.assertLogs("nuxiva.native", "WARNING"):
            self.assertEqual(native_module.build_status()["state"], "unknown")

    def test_disabled_wins(self):
        with mock.patch.dict(os.environ, {"NUXIVA_NATIVE": "0"}):
            self.assertEqual(native_module.build_status()["state"], "disabled")
            self.assertIsNone(native_module.feature("RustSentinel"))


class LoaderTests(unittest.TestCase):

    def test_module_installed_later_is_picked_up_without_restart(self):
        fake = types.ModuleType("nuxiva_native")
        fake.RustSentinel = object
        with mock.patch.dict(sys.modules, {"nuxiva_native": None}), mock.patch.dict(native_module._last_try, {"at": 0.0}):
            self.assertIsNone(native_module.feature("RustSentinel"))
            sys.modules["nuxiva_native"] = fake
            self.assertIs(native_module.feature("RustSentinel"), object)

    def test_retries_are_throttled(self):
        with mock.patch.dict(sys.modules, {"nuxiva_native": None}), mock.patch.dict(native_module._last_try, {"at": 0.0}), \
                mock.patch.object(native_module.importlib, "invalidate_caches") as invalidate:
            native_module.module()
            native_module.module()
        self.assertEqual(invalidate.call_count, 1)


class StaleModuleTests(unittest.TestCase):

    def setUp(self):
        self.file = Path(tempfile.mkdtemp()) / "build.json"
        self.fake = types.ModuleType("nuxiva_native")
        self.fake.RustPresenceTracker = object
        for patcher in (mock.patch.object(native_module, "BUILD_FILE", self.file),
                        mock.patch.dict(sys.modules, {"nuxiva_native": self.fake}),
                        mock.patch.dict(native_module._loaded, {"module": None, "rev": "", "warned": False}),
                        mock.patch.dict(os.environ, {"NUXIVA_NATIVE": "auto"})):
            patcher.start()
            self.addCleanup(patcher.stop)

    def build(self, state, rev):
        self.file.write_text(json.dumps({"state": state, "stage": "wheel", "at": 1, "rev": rev}), encoding="utf-8")

    def test_module_rebuilt_after_load_is_not_used_until_restart(self):
        self.build("ready", "a" * 16)
        self.assertIs(native_module.feature("RustPresenceTracker"), object)
        self.build("building", "b" * 16)
        with self.assertLogs("nuxiva.native", "WARNING"):
            self.assertIsNone(native_module.feature("RustPresenceTracker"))
        self.build("ready", "b" * 16)
        self.assertIsNone(native_module.feature("RustPresenceTracker"))
        self.assertTrue(native_module.stale())

    def test_module_loaded_during_build_stays_untrusted(self):
        self.build("building", "c" * 16)
        with self.assertLogs("nuxiva.native", "WARNING"):
            self.assertIsNone(native_module.module())
        self.build("ready", "c" * 16)
        self.assertIsNone(native_module.module())

    def test_without_build_record_module_is_trusted(self):
        self.assertIs(native_module.feature("RustPresenceTracker"), object)
        self.assertFalse(native_module.stale())

    def test_invalid_rev_is_ignored(self):
        self.build("ready", "a" * 16)
        native_module.module()
        self.build("ready", "../../etc")
        self.assertFalse(native_module.stale())


class SentinelStatusTests(unittest.TestCase):

    def test_status_reports_build_state(self):
        import asyncio
        from features.sentinel import api
        with mock.patch.dict(os.environ, {"NUXIVA_NATIVE": "0"}):
            response = asyncio.run(api.sentinel_status("admin"))
        body = json.loads(response.body)
        self.assertEqual((body["native"], body["build"]["state"]), (False, "disabled"))
