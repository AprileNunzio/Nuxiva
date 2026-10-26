import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from access import require_admin
from features.google import accounts as accounts_module
from features.google import api as google_api
from features.google.app import oauth
from features.google.constants import SERVICES
from features.google.gservices import google
from features.people import people, private_store
from sealed import SealedFile

ALL_SCOPES = ["openid", "email"] + [x for d in SERVICES.values() for x in d["scopes"]]
PARTIAL = ["openid"] + SERVICES["calendar"]["scopes"] + SERVICES["gmail"]["scopes"]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        store = SealedFile(root / "g.vault", root / "g.key")
        patches = (mock.patch.object(accounts_module, "_store", store), mock.patch.object(people, "PEOPLE_DIR", root),
                   mock.patch.object(private_store, "KEY_FILE", root / "people.key"), mock.patch.object(google_api.store, "event"))
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        accounts_module.accounts._data = {}
        google.sessions.clear()
        people.ensure("anna", "Anna Rossi")
        app = FastAPI()
        app.include_router(google_api.admin_routes)
        app.dependency_overrides[require_admin] = lambda: "admin"
        self.client = TestClient(app)
        self.addCleanup(self.tmp.cleanup)

    def link(self, scopes):
        accounts_module.accounts.put("anna", {"refresh": "r" * 20, "scopes": scopes, "email": "a@x.it"})


class ServiceTest(Base):
    def test_disabling_one_service_keeps_the_others(self):
        self.link(PARTIAL)
        self.assertEqual(set(accounts_module.accounts.granted(accounts_module.accounts.get("anna"))), {"calendar", "gmail"})
        self.assertEqual(self.client.delete("/api/google/anna/services/gmail").json(), {"unlinked": False})
        self.assertEqual(accounts_module.accounts.granted(accounts_module.accounts.get("anna")), ["calendar"])

    def test_disabled_service_survives_a_token_refresh(self):
        self.link(PARTIAL)
        self.client.delete("/api/google/anna/services/gmail")
        accounts_module.accounts.put("anna", {"scopes": PARTIAL})
        self.assertNotIn("gmail", accounts_module.accounts.granted(accounts_module.accounts.get("anna")))

    def test_reenabling_a_covered_service_needs_no_google_visit(self):
        self.link(PARTIAL)
        self.client.delete("/api/google/anna/services/gmail")
        self.assertEqual(self.client.post("/api/google/anna/services/gmail").json(), {"url": None})
        self.assertIn("gmail", accounts_module.accounts.granted(accounts_module.accounts.get("anna")))

    def test_enabling_a_new_service_returns_a_google_url_for_that_service_only(self):
        self.link(PARTIAL)
        with mock.patch.object(google_api.google, "auth_url", return_value="https://accounts.google.com/x") as url:
            self.assertEqual(self.client.post("/api/google/anna/services/drive").json(), {"url": "https://accounts.google.com/x"})
        url.assert_called_once_with("anna", ["drive"])

    def test_link_without_services_uses_the_defaults(self):
        with mock.patch.object(oauth, "credentials", return_value=("cid", "secret")):
            url = self.client.post("/api/google/anna/auth-url", content="{}").json()["url"]
        self.assertTrue(url.startswith("https://accounts.google.com/"))
        self.assertIn("calendar", url)

    def test_link_without_credentials_explains_why(self):
        with mock.patch.object(oauth, "credentials", return_value=("", "")):
            response = self.client.post("/api/google/anna/auth-url", content="{}")
        self.assertEqual(response.status_code, 400)

    def test_last_service_off_unlinks_the_account(self):
        self.link(SERVICES["calendar"]["scopes"])
        with mock.patch.object(google_api.google, "unlink", new=mock.AsyncMock()) as unlink:
            self.assertEqual(self.client.delete("/api/google/anna/services/calendar").json(), {"unlinked": True})
        unlink.assert_awaited_once()

    def test_invalid_requests(self):
        self.assertEqual(self.client.delete("/api/google/anna/services/calendar").status_code, 400)
        self.assertEqual(self.client.post("/api/google/anna/services/boh").status_code, 400)
        self.assertEqual(self.client.delete("/api/google/nessuno/services/calendar").status_code, 404)

    def test_person_state_lists_every_service(self):
        self.link(PARTIAL)
        rows = {s["id"]: s["granted"] for s in google.person_state("anna")["services"]}
        self.assertTrue(rows["calendar"] and rows["gmail"])
        self.assertFalse(rows["drive"])
        self.assertIn("health", rows)


if __name__ == "__main__":
    unittest.main()


class ReminderTest(Base):
    def test_each_person_has_their_own_value_with_a_default(self):
        self.assertEqual(google.reminder_minutes("anna"), 10)
        self.link(PARTIAL)
        self.assertEqual(self.client.put("/api/google/anna/reminder", json={"minutes": 25}).json(), {"minutes": 25})
        self.assertEqual(google.reminder_minutes("anna"), 25)
        people.ensure("luca", "Luca Bianchi")
        self.assertEqual(google.reminder_minutes("luca"), 10)
        self.assertEqual(google.person_state("anna")["remind_min"], 25)

    def test_zero_means_never_and_invalid_values_are_rejected(self):
        self.link(PARTIAL)
        self.assertEqual(self.client.put("/api/google/anna/reminder", json={"minutes": 0}).json(), {"minutes": 0})
        self.assertEqual(google.reminder_minutes("anna"), 0)
        for bad in (-1, 241, "10", None, True, 1.5):
            self.assertEqual(self.client.put("/api/google/anna/reminder", json={"minutes": bad}).status_code, 400, bad)

    def test_unlinked_person_cannot_set_it(self):
        self.assertEqual(self.client.put("/api/google/anna/reminder", json={"minutes": 5}).status_code, 409)
        self.assertEqual(self.client.put("/api/google/nessuno/reminder", json={"minutes": 5}).status_code, 404)

    def test_global_setting_is_gone_from_the_feature(self):
        import json
        manifest = json.loads((Path(__file__).resolve().parents[1] / "features" / "google" / "feature.json").read_text(encoding="utf-8"))
        self.assertNotIn("NUXIVA_GOOGLE_REMIND_MIN", [s["key"] for s in manifest["settings"]])
