import hashlib
import importlib.util
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

for p in (str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1] / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

import updater
from agenti.nodes.registry import Registry

SATELLITE = Path(__file__).resolve().parents[2] / "client_satellite" / "linux_edge" / "satellite.py"


def load_agent(directory: Path):
    target = directory / "satellite.py"
    target.write_bytes(SATELLITE.read_bytes())
    spec = importlib.util.spec_from_file_location("satellite_update_under_test", target)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.UPDATE_STATE = directory / "state.json"
    return module, target


class RegistryTrackingTest(unittest.TestCase):
    def setUp(self):
        self.node = {"id": "salotto", "name": "Salotto"}

    def track(self, update):
        Registry._track_update(self.node, update)

    def test_ignores_garbage(self):
        self.track({"state": "exploding"})
        self.track("x")
        self.assertNotIn("update", self.node)

    def test_records_transitions_only_once(self):
        now = time.time()
        self.track({"state": "installing", "version": "5.8.4", "channel": "debian"})
        self.track({"state": "installing", "version": "5.8.4", "channel": "debian", "last_check": now - 1})
        self.track({"state": "idle", "version": "5.8.4", "channel": "debian", "last_success": now - 1})
        self.track({"state": "idle", "version": "5.8.4", "channel": "debian", "last_success": now - 1, "last_check": now})
        self.assertEqual([e["state"] for e in self.node["update_history"]], ["installing", "idle"])

    def test_failure_keeps_error_code_in_history(self):
        now = time.time()
        self.track({"state": "rolled_back", "last_error": {"code": "boot_failed", "at": now - 2}})
        self.assertEqual(self.node["update_history"][-1]["code"], "boot_failed")

    def test_history_is_capped(self):
        now = time.time()
        for index in range(60):
            self.track({"state": "idle", "last_success": now - 100 + index})
        self.assertEqual(len(self.node["update_history"]), 20)


class AgentUpdateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.agent, self.path = load_agent(self.dir)

    def tearDown(self):
        self.tmp.cleanup()

    def test_report_defaults_to_idle(self):
        report = self.agent.update_report()
        self.assertEqual((report["state"], report["channel"], report["version"]), ("idle", "debian", self.agent.VERSION))

    def test_hash_mismatch_never_replaces_the_agent(self):
        class Reply:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self):
                return b"print('evil')"

        before = self.path.read_bytes()
        with mock.patch.object(self.agent.urllib.request, "urlopen", return_value=Reply()):
            self.agent.self_update({"server": "http://x"}, "0" * 64)
        self.assertEqual(self.path.read_bytes(), before)
        state = self.agent.update_state()
        self.assertEqual((state["state"], state["last_error"]["code"]), ("failed", "hash_mismatch"))

    def test_broken_candidate_fails_selftest_and_is_not_installed(self):
        broken = b"raise SystemExit(7)\n"

        class Reply:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self):
                return broken

        before = self.path.read_bytes()
        with mock.patch.object(self.agent.urllib.request, "urlopen", return_value=Reply()), \
                mock.patch.object(self.agent, "restart") as restart:
            self.agent.self_update({"server": "http://x"}, hashlib.sha256(broken).hexdigest())
        restart.assert_not_called()
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.agent.update_state()["last_error"]["code"], "selftest_failed")
        self.assertFalse(self.path.with_suffix(".new").exists())

    def test_good_candidate_is_installed_with_backup(self):
        good = SATELLITE.read_bytes() + b"\nMARK = 1\n"

        class Reply:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self):
                return good

        before = self.path.read_bytes()
        with mock.patch.object(self.agent.urllib.request, "urlopen", return_value=Reply()), \
                mock.patch.object(self.agent, "restart") as restart:
            self.agent.self_update({"server": "http://x"}, hashlib.sha256(good).hexdigest())
        restart.assert_called_once()
        self.assertEqual(self.path.read_bytes(), good)
        self.assertEqual(self.path.with_suffix(".bak").read_bytes(), before)
        self.assertEqual(self.agent.update_state()["state"], "installing")

    def test_crash_loop_rolls_back_and_blacklists_the_hash(self):
        backup = self.path.with_suffix(".bak")
        backup.write_bytes(b"# previous\n")
        self.agent.update_state(state="installing", boots=2, target_sha="a" * 64)
        with mock.patch.object(self.agent, "restart") as restart:
            self.agent.settle_update()
        restart.assert_called_once()
        self.assertEqual(self.path.read_bytes(), b"# previous\n")
        state = self.agent.update_state()
        self.assertEqual((state["state"], state["bad_sha"], state["last_error"]["code"]), ("rolled_back", "a" * 64, "boot_failed"))

    def test_first_boots_count_then_heartbeat_confirms(self):
        self.agent.update_state(state="installing", boots=0, target_sha="b" * 64)
        self.agent.settle_update()
        self.assertEqual(self.agent.update_state()["boots"], 1)
        self.agent.confirm_update()
        state = self.agent.update_state()
        self.assertEqual((state["state"], state["boots"], state["last_error"]), ("idle", 0, None))
        self.assertGreater(state["last_success"], 0)

    def test_selftest_flag_prints_version(self):
        import subprocess

        out = subprocess.run([sys.executable, str(self.path), "--selftest"], capture_output=True, text=True, check=True)
        self.assertEqual(out.stdout.strip(), self.agent.VERSION)


class DeferralTest(unittest.IsolatedAsyncioTestCase):
    async def test_automatic_update_waits_for_the_end_of_a_conversation(self):
        info = {"available": True}
        store = mock.Mock(update=info, phase="READY", pipeline_failed=False)
        with mock.patch.object(updater, "store", store), \
                mock.patch.object(updater, "voice_busy", return_value=True), \
                mock.patch.object(updater, "check", mock.AsyncMock()) as check, \
                mock.patch.object(updater, "apply", mock.AsyncMock()) as apply, \
                mock.patch.object(updater, "sh", mock.AsyncMock()), \
                mock.patch("agenti.update_center.system_runner.sync_auto_security", mock.AsyncMock()), \
                mock.patch.object(updater, "env_get", lambda key, default="": {"NUXIVA_UPDATE_WINDOW": "off"}.get(key, default)):
            await updater._scheduled_cycle(False)
        apply.assert_not_called()
        check.assert_awaited()
        self.assertTrue(info["deferred"])

    async def test_stuck_system_ignores_the_conversation_guard(self):
        info = {"available": True}
        store = mock.Mock(update=info, phase="ERROR", pipeline_failed=False)
        with mock.patch.object(updater, "store", store), \
                mock.patch.object(updater, "voice_busy", return_value=True), \
                mock.patch.object(updater, "check", mock.AsyncMock()), \
                mock.patch.object(updater, "apply", mock.AsyncMock(return_value=False)) as apply, \
                mock.patch.object(updater, "sh", mock.AsyncMock()), \
                mock.patch("agenti.update_center.system_runner.sync_auto_security", mock.AsyncMock()), \
                mock.patch.object(updater, "env_get", lambda key, default="": {"NUXIVA_UPDATE_WINDOW": "off"}.get(key, default)):
            await updater._scheduled_cycle(True)
        apply.assert_awaited()
        self.assertFalse(info["deferred"])


if __name__ == "__main__":
    unittest.main()
