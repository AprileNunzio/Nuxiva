import unittest
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _ROOT / "installer_wizard" / "backend"
_SERVER = _ROOT / "server"
for p in (str(_ROOT), str(_BACKEND), str(_SERVER)):
    if p not in sys.path:
        sys.path.insert(0, p)

from update_api import get_update_status, update_schedule, run_collaudo, trigger_update, ScheduleUpdateRequest, TriggerUpdateRequest


class UpdaterApiTests(unittest.TestCase):
    def test_get_update_status_structure(self):
        status = get_update_status()
        self.assertIn("current_version", status)
        self.assertIn("latest_version", status)
        self.assertIn("scheduled_time", status)
        self.assertIn("synchronized", status)
        self.assertIn("auto_rollback", status)
        self.assertIn("nodes", status)
        self.assertIsInstance(status["nodes"], list)
        self.assertGreater(len(status["nodes"]), 0)

    def test_update_schedule_policy(self):
        req = ScheduleUpdateRequest(
            scheduled_time="03:00",
            synchronized=True,
            auto_rollback=True,
            channel="release-candidate"
        )
        res = update_schedule(req)
        self.assertEqual(res["scheduled_time"], "03:00")
        self.assertTrue(res["synchronized"])
        self.assertTrue(res["auto_rollback"])
        self.assertEqual(res["channel"], "release-candidate")

    def test_collaudo_real_hardware_diagnostics(self):
        result = run_collaudo()
        self.assertIn("all_passed", result)
        self.assertIn("tests", result)
        test_ids = [t["id"] for t in result["tests"]]
        self.assertIn("ram_margin", test_ids)
        self.assertIn("disk_margin", test_ids)
        self.assertIn("network_socket", test_ids)
        self.assertIn("crdt_engine", test_ids)

        for t in result["tests"]:
            self.assertIn(t["status"], ("PASS", "WARN", "FAIL"))
            self.assertTrue(t["passed"])

    def test_trigger_cluster_update(self):
        req = TriggerUpdateRequest(immediate=True, channel="stable")
        res = trigger_update(req)
        self.assertEqual(res["status"], "complete")
        self.assertGreater(len(res["logs"]), 0)


if __name__ == "__main__":
    unittest.main()
