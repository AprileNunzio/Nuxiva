import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from access import require_admin
from features.people import people, private_store
from features.people.fingerprint import api as fp_api
from features.people.fingerprint import service as fp_service
from features.people.fingerprint import store as fp_store
from features.people.fingerprint.readers import readers
from features.people.fingerprint.service import service
from features.people.fingerprint.store import bindings


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        patches = (mock.patch.object(people, "PEOPLE_DIR", root), mock.patch.object(private_store, "KEY_FILE", root / "people.key"),
                   mock.patch.object(fp_store, "FILE", root / "fp.vault"), mock.patch.object(fp_service.store, "event"),
                   mock.patch.object(fp_api.store, "event"),
                   mock.patch.object(fp_service.registry, "data", {"nodes": {"n1": {"id": "n1", "room": "Cucina"}}}))
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        readers.clear()
        service._enroll.clear()
        service._fails.clear()
        service._locked.clear()
        service._recent.clear()
        people.ensure("anna", "Anna Rossi")
        self.addCleanup(self.tmp.cleanup)

    def report(self, events, now=1000.0):
        return service.node_report("n1", {"readers": [{"reader": "r1", "transport": "bluetooth", "label": "Lettore", "events": events}]}, now)

    def token(self):
        return next(iter(service._enroll))


class FlowTest(Base):
    def test_reader_is_discovered_with_room_and_transport(self):
        self.report([])
        row = readers.listing(1000.0)[0]
        self.assertEqual((row["room"], row["transport"], row["online"]), ("Cucina", "bluetooth", True))

    def test_enroll_then_match_requires_enabled(self):
        self.report([])
        service.start_enroll("anna", "right_index", "n1:r1", 1000.0)
        order = service.node_report("n1", {"readers": []}, 1001.0)["enroll"]
        self.assertEqual((order[0]["reader"], order[0]["finger"]), ("r1", "right_index"))
        done = self.report([{"type": "enrolled", "template": "tpl-1", "enrollment": order[0]["token"]}], 1002.0)
        self.assertEqual(done["results"][0]["type"], "enrolled")
        denied = self.report([{"type": "match", "template": "tpl-1"}], 1003.0)
        self.assertEqual(denied["results"][0]["type"], "denied")
        bindings.set_enabled("anna", True)
        ok = self.report([{"type": "match", "template": "tpl-1"}], 1004.0)["results"][0]
        self.assertEqual((ok["type"], ok["slug"], ok["room"]), ("matched", "anna", "Cucina"))
        self.assertEqual(service.last_seen("anna", 1005.0)["room"], "Cucina")

    def test_unknown_template_and_wrong_token_are_rejected(self):
        self.report([])
        bindings.set_enabled("anna", True)
        self.assertEqual(self.report([{"type": "match", "template": "nope"}])["results"][0]["type"], "denied")
        self.assertEqual(self.report([{"type": "enrolled", "template": "x", "enrollment": "forged"}])["results"][0]["type"], "enroll_rejected")

    def test_enrollment_token_is_single_use_and_expires(self):
        self.report([])
        service.start_enroll("anna", "left_thumb", "n1:r1", 1000.0)
        token = self.token()
        late = self.report([{"type": "enrolled", "template": "t", "enrollment": token}], 1000.0 + 500)
        self.assertEqual(late["results"][0]["type"], "enroll_rejected")

    def test_brute_force_locks_the_reader(self):
        self.report([])
        bindings.set_enabled("anna", True)
        for i in range(5):
            self.report([{"type": "match", "template": f"bad{i}"}], 1000.0 + i)
        self.assertEqual(self.report([{"type": "match", "template": "bad"}], 1010.0)["results"][0]["type"], "locked")
        self.assertNotEqual(self.report([{"type": "match", "template": "bad"}], 1000.0 + 500)["results"][0]["type"], "locked")

    def test_invalid_reader_and_events_are_ignored(self):
        out = service.node_report("n1", {"readers": [{"reader": "../x", "events": [{"type": "match"}]}, "x"]}, 1000.0)
        self.assertEqual(out["results"], [])
        self.assertEqual(readers.listing(1000.0), [])

    def test_forget_removes_templates_and_setting(self):
        self.report([])
        service.start_enroll("anna", "right_index", "n1:r1", 1000.0)
        self.report([{"type": "enrolled", "template": "tpl-1", "enrollment": self.token()}], 1001.0)
        bindings.set_enabled("anna", True)
        self.assertEqual(bindings.forget("anna"), 1)
        self.assertFalse(bindings.enabled("anna"))
        self.assertIsNone(bindings.resolve("n1:r1", "tpl-1"))

    def test_templates_are_stored_sealed(self):
        self.report([])
        service.start_enroll("anna", "right_index", "n1:r1", 1000.0)
        self.report([{"type": "enrolled", "template": "secret-template-id", "enrollment": self.token()}], 1001.0)
        self.assertNotIn(b"secret-template-id", fp_store.FILE.read_bytes())


class ApiTest(Base):
    def setUp(self):
        super().setUp()
        app = FastAPI()
        app.include_router(fp_api.admin_routes)
        app.include_router(fp_api.public_routes)
        app.dependency_overrides[require_admin] = lambda: "admin"
        self.client = TestClient(app)
        patch = mock.patch.object(fp_api.local, "discover", new=mock.AsyncMock(return_value=0))
        patch.start()
        self.addCleanup(patch.stop)

    def test_toggle_and_state(self):
        self.assertFalse(self.client.get("/api/people/anna/fingerprint").json()["enabled"])
        self.assertEqual(self.client.put("/api/people/anna/fingerprint", json={"enabled": True}).json(), {"enabled": True})
        self.assertTrue(self.client.get("/api/people/anna/fingerprint").json()["enabled"])
        self.assertEqual(self.client.put("/api/people/anna/fingerprint", json={"enabled": "si"}).status_code, 400)

    def test_enroll_needs_a_reachable_reader_and_valid_finger(self):
        self.assertEqual(self.client.post("/api/people/anna/fingerprint/enroll", json={"finger": "right_index", "reader": "n1:r1"}).status_code, 400)
        self.report([], time.time())
        self.assertEqual(self.client.post("/api/people/anna/fingerprint/enroll", json={"finger": "tail", "reader": "n1:r1"}).status_code, 400)
        ok = self.client.post("/api/people/anna/fingerprint/enroll", json={"finger": "right_index", "reader": "n1:r1"})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(self.client.get("/api/people/anna/fingerprint").json()["pending"]["finger"], "right_index")

    def test_unknown_person_and_bad_node_auth(self):
        self.assertEqual(self.client.get("/api/people/nessuno/fingerprint").status_code, 404)
        self.assertEqual(self.client.post("/api/fingerprint/node", json={}).status_code, 401)

    def test_connector_status(self):
        self.assertEqual(fp_api.person_status("anna")["linked"], False)


if __name__ == "__main__":
    unittest.main()
