import unittest
from unittest import mock
from fastapi.testclient import TestClient

import nuxiva_supervisor
import setup_api
from state import store

HEADERS = {"X-Nuxiva-Request": "1"}


class SetupUpdateSyncTest(unittest.TestCase):
    def setUp(self):
        self.public = TestClient(nuxiva_supervisor.public)
        self.private_patch = mock.patch.object(setup_api, "_private_client", lambda r: True)
        self.local_patch = mock.patch.object(setup_api, "is_local", lambda r: True)
        self.done_patch = mock.patch.object(setup_api, "done", return_value=False)
        self.private_patch.start()
        self.local_patch.start()
        self.done_patch.start()

    def tearDown(self):
        self.done_patch.stop()
        self.local_patch.stop()
        self.private_patch.stop()

    def test_setup_update_status(self):
        with mock.patch("updater.current_rev", return_value="deadbeef12"), \
             mock.patch.object(store, "update", {"remote_rev": "deadbeef12", "available": False, "changelog": []}):
            res = self.public.get("/api/setup/update")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["local_rev"], "deadbeef12")
            self.assertFalse(data["available"])

    def test_setup_update_sync_uptodate(self):
        with mock.patch("updater.check", return_value={"available": False, "check_error": None}), \
             mock.patch("updater.current_rev", return_value="1122334455"):
            res = self.public.post("/api/setup/update/sync", headers=HEADERS)
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertTrue(data["success"])
            self.assertFalse(data["applied"])
            self.assertTrue(data["uptodate"])
            self.assertEqual(data["local_rev"], "1122334455")

    def test_setup_update_sync_applies_new_commit(self):
        with mock.patch("updater.check", return_value={"available": True, "target_rev": "abcdef1234", "check_error": None, "changelog": ["feat: new update"]}), \
             mock.patch("updater.apply", return_value=True), \
             mock.patch("updater.current_rev", return_value="abcdef1234"):
            res = self.public.post("/api/setup/update/sync", headers=HEADERS)
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertTrue(data["success"])
            self.assertTrue(data["applied"])
            self.assertEqual(data["target_rev"], "abcdef1234")
            self.assertEqual(data["changelog"], ["feat: new update"])

    def test_setup_update_sync_error_handling(self):
        with mock.patch("updater.check", return_value={"available": False, "check_error": "Network timeout"}), \
             mock.patch("updater.current_rev", return_value="1122334455"):
            res = self.public.post("/api/setup/update/sync", headers=HEADERS)
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertFalse(data["success"])
            self.assertEqual(data["error"], "Network timeout")


if __name__ == "__main__":
    unittest.main()
