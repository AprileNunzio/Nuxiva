import json
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

for p in (str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1] / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from agenti.update_center import fleet, overview

NOW = 1_800_000_000.0

REPORTS = [
    {"state": "idle", "channel": "debian", "version": "5.8.3", "last_check": NOW - 10, "last_success": NOW - 500},
    {"state": "failed", "channel": "android", "version": "5.8.2", "last_error": {"code": "Hash_Mismatch", "at": NOW - 4}},
    {"state": "exploding"},
    {"state": "idle", "channel": "weird", "version": "bad version!", "last_check": 9.9e18},
    {"state": "installing", "version": "5.8.3\n"},
    {"state": "idle", "last_error": {"code": "x" * 80}},
    {"state": "idle", "last_check": True},
    "idle",
    None,
    {"state": "failed", "channel": "windows", "last_error": {"code": "server_rejected", "at": NOW - 3, "detail": "HTTP 415"}},
    {"state": "failed", "channel": "windows", "last_error": {"code": "download_failed", "detail": "<img src=x>"}},
    {"state": "failed", "channel": "windows", "last_error": {"code": "download_failed", "detail": "x" * 81}},
]

SCENARIOS = [
    {"now": NOW, "server": {"version": "5.8.4", "state": "idle", "auto_update": True, "last_check": NOW}, "nodes": [
        {"id": "a", "online": True, "version": "5.8.4"},
        {"id": "b", "online": True, "version": "5.8.3"},
        {"id": "c", "online": False, "version": "5.8.3"},
        {"id": "d", "online": True, "version": "5.8.3", "update": {"state": "rolled_back"}},
        {"id": "e", "online": True, "version": "5.8.3", "update": {"state": "installing"}},
        {"id": "f", "online": True, "update": {"state": "awaiting_user", "version": "5.8.3"}},
        {"id": "g", "online": True},
        {"id": "../x", "online": True},
        {"id": "h", "online": True, "version": "5.8.4",
         "update_history": [{"at": NOW - 9, "state": "failed", "code": "Bad_Hash"}, {"state": "nope"}, {"at": NOW, "state": "idle"}]},
    ]},
    {"now": NOW, "server": {"version": "1", "last_error": "fetch"}, "nodes": []},
    {"now": NOW, "server": {"version": "1", "available": True}, "nodes": []},
    {"now": NOW, "server": {"version": "1", "state": "installing"}, "nodes": [{"id": "n1", "online": True, "version": "1"}]},
    {"now": NOW, "server": {"version": "1"}, "nodes": [{"id": "n1", "name": "Salotto\x00", "online": True, "version": "1"}]},
    {"now": NOW, "nodes": "bad"},
]


class FleetSanitizeTest(unittest.TestCase):
    def test_rejects_garbage(self):
        for raw in (REPORTS[2], REPORTS[7], REPORTS[8]):
            self.assertIsNone(fleet._py_sanitize(raw, NOW))

    def test_normalises_fields(self):
        report = fleet._py_sanitize(REPORTS[1], NOW)
        self.assertEqual(report["last_error"]["code"], "hash_mismatch")
        self.assertEqual(report["channel"], "android")
        loose = fleet._py_sanitize(REPORTS[3], NOW)
        self.assertEqual((loose["channel"], loose["version"], loose["last_check"]), ("other", None, None))
        self.assertIsNone(fleet._py_sanitize(REPORTS[5], NOW)["last_error"])
        self.assertIsNone(fleet._py_sanitize(REPORTS[6], NOW)["last_check"])

    def test_error_detail_is_kept_only_when_safe(self):
        self.assertEqual(fleet._py_sanitize(REPORTS[9], NOW)["last_error"]["detail"], "HTTP 415")
        self.assertNotIn("detail", fleet._py_sanitize(REPORTS[10], NOW)["last_error"])
        self.assertNotIn("detail", fleet._py_sanitize(REPORTS[11], NOW)["last_error"])

    def test_version_with_newline_is_trimmed(self):
        self.assertEqual(fleet._py_sanitize(REPORTS[4], NOW)["version"], "5.8.3")


class FleetOverviewTest(unittest.TestCase):
    def test_classification(self):
        view = fleet._py_overview(SCENARIOS[0])
        self.assertEqual([n["status"] for n in view["nodes"]],
                         ["up_to_date", "outdated", "offline", "failed", "updating", "awaiting_user", "unknown", "up_to_date"])
        self.assertEqual(view["summary"], "attention")
        self.assertEqual(view["counts"]["total"], 8)
        self.assertEqual(len(view["nodes"][-1]["history"]), 2)

    def test_server_summaries(self):
        self.assertEqual(fleet._py_overview(SCENARIOS[1])["summary"], "attention")
        self.assertEqual(fleet._py_overview(SCENARIOS[2])["summary"], "outdated")
        self.assertEqual(fleet._py_overview(SCENARIOS[3])["summary"], "updating")
        self.assertEqual(fleet._py_overview(SCENARIOS[4])["summary"], "up_to_date")
        self.assertEqual(fleet._py_overview(SCENARIOS[5])["summary"], "up_to_date")

    def test_control_characters_stripped(self):
        self.assertEqual(fleet._py_overview(SCENARIOS[4])["nodes"][0]["name"], "Salotto")


@unittest.skipUnless(fleet._rust(), "nuxiva_native with fleet functions not installed")
class FleetParityTest(unittest.TestCase):
    def test_sanitize_parity(self):
        for raw in REPORTS:
            self.assertEqual(fleet.sanitize(raw, NOW), fleet._py_sanitize(raw, NOW), raw)

    def test_overview_parity(self):
        for data in SCENARIOS:
            self.assertEqual(fleet.overview(data), fleet._py_overview(data), data)


class OverviewBuildTest(unittest.TestCase):
    def test_server_error_requires_newer_failure(self):
        with mock.patch.object(overview, "_last_installed", return_value=None):
            old = overview.server_input({"last_success": NOW, "last_failure": {"at": NOW - 5, "code": "x"}},
                                        version="1", auto_update=True, active=False, next_check=None)
            self.assertIsNone(old["last_error"])
            new = overview.server_input({"last_success": NOW - 5, "last_failure": {"at": NOW, "code": "integrity_mismatch"}},
                                        version="1", auto_update=True, active=False, next_check=None)
            self.assertEqual(new["last_error"], "integrity_mismatch")

    def test_iso_last_check_converted(self):
        with mock.patch.object(overview, "_last_installed", return_value=123.0):
            data = overview.server_input({"last_check": "2026-11-15T07:33:13+00:00"}, version="1", auto_update=False,
                                         active=True, next_check=None)
        self.assertEqual(data["last_check"], datetime(2026, 11, 15, 7, 33, 13, tzinfo=timezone.utc).timestamp())
        self.assertEqual((data["last_success"], data["state"]), (123.0, "installing"))

    def test_build_is_json_serialisable(self):
        view = overview.build({"version": "1"}, [{"id": "n1", "online": True, "version": "1", "token": "secret"}])
        self.assertNotIn("secret", json.dumps(view))
        self.assertGreater(time.time(), 0)


class OverviewApiTest(unittest.TestCase):
    def test_route_requires_admin_and_hides_secrets(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        import auth
        from agenti.update_center import api as upd_api

        app = FastAPI()
        app.include_router(upd_api.admin_routes)
        anon, admin = TestClient(app), TestClient(app)
        admin.cookies.set(auth.SESSION_COOKIE, auth.issue("root"))
        self.assertEqual(anon.get("/api/v5/updater/overview").status_code, 401)
        node = {"id": "salotto", "name": "Salotto", "type": "android", "online": True, "version": "5.8.3", "token": "secret",
                "update": {"state": "awaiting_user", "channel": "android", "version": "5.8.3", "target": "5.8.4"}}
        registry = mock.Mock(listing=mock.Mock(return_value=[node]))
        with mock.patch.object(upd_api, "_registry", return_value=registry), \
                mock.patch.object(overview, "_last_installed", return_value=None):
            res = admin.get("/api/v5/updater/overview")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["nodes"][0]["status"], "awaiting_user")
        self.assertNotIn("secret", json.dumps(data))
        self.assertEqual(data["counts"]["awaiting_user"], 1)


if __name__ == "__main__":
    unittest.main()
