import asyncio
import sys
import unittest
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
for p in (str(_ROOT), str(_ROOT / "installer_wizard"), str(_ROOT / "installer_wizard" / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from features.update_center import diagnostics, rollout
from features.update_center.policy import UpdatePolicy, in_window, load_policy, next_window, policy_to_env


class PolicyTests(unittest.TestCase):
    def test_defaults_to_nightly_window(self):
        policy = load_policy(lambda key, default: default)
        self.assertTrue(policy.auto_update)
        self.assertEqual(policy.window, "03:00")
        self.assertTrue(policy.sync_nodes)

    def test_window_off_means_anytime(self):
        env = {"NUXIVA_UPDATE_WINDOW": "off"}
        policy = load_policy(lambda key, default: env.get(key, default))
        self.assertEqual(policy.window, "")
        self.assertTrue(in_window(datetime(2026, 1, 1, 14, 0), policy.window))

    def test_in_window_spans_one_hour_including_midnight(self):
        self.assertTrue(in_window(datetime(2026, 1, 1, 3, 30), "03:00"))
        self.assertFalse(in_window(datetime(2026, 1, 1, 4, 1), "03:00"))
        self.assertTrue(in_window(datetime(2026, 1, 2, 0, 20), "23:45"))
        self.assertFalse(in_window(datetime(2026, 1, 1, 2, 59), "03:00"))

    def test_next_window(self):
        self.assertEqual(next_window(datetime(2026, 1, 1, 4, 0), "03:00"), datetime(2026, 1, 2, 3, 0))
        self.assertIsNone(next_window(datetime(2026, 1, 1, 4, 0), ""))

    def test_policy_roundtrip(self):
        policy = UpdatePolicy(auto_update=False, window="", interval_minutes=15, sync_nodes=False, require_ci=True)
        env = policy_to_env(policy)
        self.assertEqual(env["NUXIVA_UPDATE_WINDOW"], "off")
        self.assertEqual(load_policy(lambda key, default: env.get(key, default)), policy)


class DiagnosticsTests(unittest.TestCase):
    def test_failing_check_is_reported_as_fail_never_pass(self):
        async def boom():
            raise OSError("disk unreadable")

        boom.check_id = "disk"
        result = asyncio.run(diagnostics.run_all([boom]))
        self.assertFalse(result["all_passed"])
        self.assertEqual(result["tests"][0]["status"], "FAIL")
        self.assertEqual(result["tests"][0]["id"], "disk")

    def test_ci_grading(self):
        async def status(_):
            return "failure"

        result = asyncio.run(diagnostics.check_ci("abcdef123", status))
        self.assertEqual(result.status, "FAIL")

    def test_dirty_worktree_warns(self):
        async def git(*args, **kwargs):
            return 0, " M installer_wizard/backend/config.py\n"

        self.assertEqual(asyncio.run(diagnostics.check_worktree(git)).status, "WARN")


class RolloutTests(unittest.TestCase):
    def test_queue_only_known_nodes(self):
        class Registry:
            data = {"nodes": {"sat-uno": {}}}
            sent = []

            def command(self, node_id, command):
                self.sent.append((node_id, command))

        registry = Registry()
        self.assertEqual(rollout.queue_updates(registry, ["sat-uno", "ghost"]), ["sat-uno"])
        self.assertEqual(registry.sent, [("sat-uno", "update")])

    def test_view_flags_queued_update(self):
        view = rollout.node_rollout_view([{"id": "sat-uno", "name": "Uno", "online": True, "commands": ["update"]}])
        self.assertTrue(view[0]["update_queued"])
        self.assertIsNone(view[0]["version"])


if __name__ == "__main__":
    unittest.main()
