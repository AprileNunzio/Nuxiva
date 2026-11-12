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
        root = Path(tempfile.mkdtemp())
        self.file = root / "build.json"
        self.wheel = root / "wheel.json"
        self.reload = root / "reload.json"
        package = root / "site" / "nuxiva_native"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
        self.so = package / "nuxiva_native.cpython-312-x86_64-linux-gnu.so"
        self.so.write_bytes(b"old")
        self.fake = types.ModuleType("nuxiva_native")
        self.fake.__file__ = str(package / "__init__.py")
        self.fake.RustPresenceTracker = object
        for patcher in (mock.patch.object(native_module, "BUILD_FILE", self.file),
                        mock.patch.object(native_module, "WHEEL_FILE", self.wheel),
                        mock.patch.object(native_module, "RELOAD_FILE", self.reload),
                        mock.patch.dict(sys.modules, {"nuxiva_native": self.fake}),
                        mock.patch.dict(native_module._loaded, {"module": None, "identity": None, "warned": False}),
                        mock.patch.dict(os.environ, {"NUXIVA_NATIVE": "auto"})):
            patcher.start()
            self.addCleanup(patcher.stop)

    def build(self, state, rev, stage="wheel"):
        self.file.write_text(json.dumps({"state": state, "stage": stage, "at": 1, "rev": rev}), encoding="utf-8")

    def install(self, rev, payload=b"new"):
        tmp = self.so.with_suffix(".tmp")
        tmp.write_bytes(payload)
        tmp.replace(self.so)
        self.wheel.write_text(json.dumps({"rev": rev, "at": 2}), encoding="utf-8")

    def test_new_build_of_same_sources_keeps_module_in_use(self):
        self.install("a" * 16, b"old")
        self.build("ready", "a" * 16, "done")
        native_module.module()
        self.build("building", "a" * 16)
        self.assertIs(native_module.feature("RustPresenceTracker"), object)

    def test_wheel_replaced_after_load_requests_reload(self):
        self.build("ready", "a" * 16, "done")
        self.assertIs(native_module.feature("RustPresenceTracker"), object)
        self.install("b" * 16)
        self.build("ready", "b" * 16, "egress")
        with self.assertLogs("nuxiva.native", "WARNING"):
            self.assertIsNone(native_module.feature("RustPresenceTracker"))
        self.assertTrue(native_module.reload_needed())
        self.assertEqual(native_module.build_status()["state"], "restarting")

    def test_sources_ahead_of_installed_wheel_are_not_trusted(self):
        self.install("a" * 16, b"old")
        native_module.module()
        self.build("building", "b" * 16)
        with self.assertLogs("nuxiva.native", "WARNING"):
            self.assertIsNone(native_module.module())
        self.assertFalse(native_module.reload_needed())
        self.build("failed", "b" * 16)
        self.assertIsNone(native_module.module())

    def test_later_stage_failure_keeps_current_wheel(self):
        self.install("a" * 16, b"old")
        self.build("failed", "a" * 16, "display")
        self.assertIs(native_module.feature("RustPresenceTracker"), object)
        self.assertFalse(native_module.stale())

    def test_without_build_record_module_is_trusted(self):
        self.assertIs(native_module.feature("RustPresenceTracker"), object)
        self.assertFalse(native_module.stale())

    def test_invalid_rev_is_ignored(self):
        self.install("a" * 16, b"old")
        native_module.module()
        self.build("building", "../../etc")
        self.assertFalse(native_module.stale())

    def test_reload_is_claimed_once_per_installed_wheel(self):
        native_module.module()
        self.install("b" * 16)
        self.assertTrue(native_module.claim_reload(now=100.0))
        self.assertFalse(native_module.claim_reload(now=200.0))
        self.assertTrue(native_module.claim_reload(now=100.0 + native_module.RELOAD_GUARD_SECONDS + 1))
        self.install("c" * 16, b"newer")
        self.assertTrue(native_module.claim_reload(now=300.0))

    def test_module_without_file_never_requests_reload(self):
        del self.fake.__file__
        native_module.module()
        self.assertFalse(native_module.reload_needed())
        self.assertFalse(native_module.claim_reload())


class ReloadLoopTests(unittest.TestCase):

    def setUp(self):
        import orchestrator
        self.orchestrator = orchestrator
        for patcher in (mock.patch.object(native_module, "reload_needed", return_value=True),
                        mock.patch.object(native_module, "claim_reload", return_value=True),
                        mock.patch.object(orchestrator.store, "phase", "READY"),
                        mock.patch.object(orchestrator.store, "event"),
                        mock.patch.dict(os.environ, {"INVOCATION_ID": "x"})):
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_check(self):
        import asyncio
        sh = mock.AsyncMock(return_value=(0, ""))
        with mock.patch.object(self.orchestrator.health, "sh", sh):
            done = asyncio.run(self.orchestrator.native_reload_check())
        return done, sh

    def test_restarts_supervisor_when_idle(self):
        done, sh = self.run_check()
        self.assertTrue(done)
        sh.assert_awaited_once_with("systemctl", "restart", "--no-block", "nuxiva-supervisor.service", timeout=15)

    def test_waits_while_steps_run_or_boot_is_in_progress(self):
        with mock.patch.object(self.orchestrator.store, "phase", "UPDATING"):
            self.assertFalse(self.run_check()[0])
        with mock.patch.object(self.orchestrator.orch.lock, "locked", return_value=True):
            self.assertFalse(self.run_check()[0])

    def test_never_restarts_outside_systemd(self):
        with mock.patch.dict(os.environ, {"INVOCATION_ID": ""}):
            done, sh = self.run_check()
        self.assertFalse(done)
        sh.assert_not_awaited()

    def test_failed_restart_is_reported(self):
        import asyncio
        sh = mock.AsyncMock(return_value=(1, "boom"))
        with mock.patch.object(self.orchestrator.health, "sh", sh), self.assertLogs("nuxiva.supervisor", "ERROR"):
            self.assertFalse(asyncio.run(self.orchestrator.native_reload_check()))


class SentinelStatusTests(unittest.TestCase):

    def test_status_reports_build_state(self):
        import asyncio
        from features.sentinel import api
        with mock.patch.dict(os.environ, {"NUXIVA_NATIVE": "0"}):
            response = asyncio.run(api.sentinel_status("admin"))
        body = json.loads(response.body)
        self.assertEqual((body["native"], body["build"]["state"]), (False, "disabled"))
