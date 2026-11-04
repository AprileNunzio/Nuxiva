import sys
import unittest
from unittest import mock

sys.modules.setdefault("cv2", mock.MagicMock())

from access import require_admin
from fastapi.testclient import TestClient
import nuxiva_supervisor
from os_notification import NotificationManager
from os_memory import MemoryManager
from os_process import ProcessManager
from features.auto_update.boot_updater import BootUpdater


class TestOSNotificationManager(unittest.TestCase):
    def setUp(self):
        self.mgr = NotificationManager(max_history=10, cooldown_s=1.0)

    def test_notify_creates_and_retrieves(self):
        notif = self.mgr.notify(
            level="WARNING",
            code="test_code",
            label_key="test_key",
            message="Test alert",
            details={"detail1": "value1"},
            action={"appId": "hub"},
        )
        self.assertIsNotNone(notif)
        self.assertEqual(notif.code, "test_code")
        self.assertEqual(notif.level, "WARNING")
        items = self.mgr.get_all()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["code"], "test_code")

    def test_cooldown_prevents_duplicate_spam(self):
        n1 = self.mgr.notify("INFO", "duplicate", "key", "msg 1")
        n2 = self.mgr.notify("INFO", "duplicate", "key", "msg 2")
        self.assertIsNotNone(n1)
        self.assertIsNone(n2)
        self.assertEqual(self.mgr.count(), 1)

    def test_force_bypasses_cooldown(self):
        n1 = self.mgr.notify("INFO", "duplicate", "key", "msg 1")
        n2 = self.mgr.notify("INFO", "duplicate", "key", "msg 2", force=True)
        self.assertIsNotNone(n1)
        self.assertIsNotNone(n2)
        self.assertEqual(self.mgr.count(), 2)

    def test_clear_removes_all(self):
        self.mgr.notify("INFO", "c1", "k1", "m1")
        self.mgr.notify("INFO", "c2", "k2", "m2")
        self.assertEqual(self.mgr.count(), 2)
        self.mgr.clear()
        self.assertEqual(self.mgr.count(), 0)


class TestOSMemoryManager(unittest.TestCase):
    def setUp(self):
        self.mem = MemoryManager(warn_percent=80.0, critical_percent=90.0, min_free_mb=1000.0, recovery_percent=70.0)

    def test_normal_memory_state(self):
        with mock.patch("psutil.virtual_memory") as mock_vm, mock.patch("psutil.swap_memory") as mock_swap:
            mock_vm.return_value = mock.Mock(total=16000 * 1024 * 1024, available=10000 * 1024 * 1024, percent=40.0)
            mock_swap.return_value = mock.Mock(percent=5.0)
            res = self.mem.sample()
            self.assertEqual(res["state"], "normal")
            self.assertFalse(res["throttled"])

    def test_warning_memory_state(self):
        with mock.patch("psutil.virtual_memory") as mock_vm, mock.patch("psutil.swap_memory") as mock_swap:
            mock_vm.return_value = mock.Mock(total=16000 * 1024 * 1024, available=800 * 1024 * 1024, percent=82.0)
            mock_swap.return_value = mock.Mock(percent=10.0)
            res = self.mem.sample()
            self.assertEqual(res["state"], "warning")

    def test_critical_memory_state_triggers_throttling(self):
        with mock.patch("psutil.virtual_memory") as mock_vm, mock.patch("psutil.swap_memory") as mock_swap:
            mock_vm.return_value = mock.Mock(total=16000 * 1024 * 1024, available=300 * 1024 * 1024, percent=95.0)
            mock_swap.return_value = mock.Mock(percent=30.0)
            res = self.mem.sample()
            self.assertEqual(res["state"], "critical")
            self.assertTrue(self.mem.is_throttled())


class TestOSProcessManager(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.pm = ProcessManager()

    async def test_process_registration_and_execution(self):
        executed = []

        async def worker():
            executed.append("done")

        self.pm.register("test_proc", worker, interval=0.0)
        task = self.pm.spawn("test_proc")
        self.assertIsNotNone(task)
        await task
        self.assertEqual(executed, ["done"])
        procs = self.pm.get_all()
        self.assertEqual(len(procs), 1)
        self.assertEqual(procs[0]["name"], "test_proc")
        self.assertEqual(procs[0]["status"], "completed")


class TestBootUpdater(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bu = BootUpdater()

    async def test_boot_check_executes_self_healing(self):
        with mock.patch("features.auto_update.boot_updater.self_healer.run_all", return_value={"test": True}) as mock_heal:
            with mock.patch("updater.priority_update", mock.AsyncMock(return_value=False)):
                res = await self.bu.execute_boot_check()
                self.assertTrue(res.get("ok"))
                self.assertEqual(res.get("healing"), {"test": True})
                mock_heal.assert_called_once()


class TestOSApiEndpoints(unittest.TestCase):
    def setUp(self):
        nuxiva_supervisor.admin.dependency_overrides[require_admin] = lambda: "admin_user"
        self.client = TestClient(nuxiva_supervisor.admin)

    def tearDown(self):
        nuxiva_supervisor.admin.dependency_overrides.pop(require_admin, None)

    def test_get_os_status(self):
        res = self.client.get("/api/os/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("uptime_seconds", data)
        self.assertIn("memory_state", data)
        self.assertIn("notifications_count", data)

    def test_get_os_memory(self):
        res = self.client.get("/api/os/memory")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_mb", data)
        self.assertIn("percent", data)
        self.assertIn("top_processes", data)

    def test_get_os_processes(self):
        res = self.client.get("/api/os/processes")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("processes", data)

    def test_get_os_notifications(self):
        res = self.client.get("/api/os/notifications")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("notifications", data)

    def test_clear_notifications_with_csrf(self):
        headers = {"X-Nuxiva-Request": "1"}
        res = self.client.post("/api/os/notifications/clear", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json().get("ok"))

    def test_send_test_notification_with_csrf(self):
        headers = {"X-Nuxiva-Request": "1"}
        res = self.client.post("/api/os/notifications/test", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json().get("ok"))


if __name__ == "__main__":
    unittest.main()
