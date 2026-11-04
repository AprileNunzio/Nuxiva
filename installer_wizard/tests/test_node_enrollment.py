import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from features.nodes import enroll_routes
from features.nodes import enrollment as enrollment_module
from features.nodes import registry as registry_module


class TokensTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        patcher = mock.patch.object(enrollment_module, "TOKENS_FILE", self.dir / "tokens.json")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.tokens = enrollment_module.EnrollmentTokens()

    def test_token_is_single_use_and_stored_only_as_a_hash(self):
        token, _ = self.tokens.issue()
        raw = enrollment_module.TOKENS_FILE.read_text(encoding="utf-8")
        self.assertNotIn(token, raw)
        digest = self.tokens.verify(token)
        self.tokens.burn(digest)
        with self.assertRaises(enrollment_module.EnrollmentError) as ctx:
            self.tokens.verify(token)
        self.assertEqual(ctx.exception.code, "enroll_token_invalid")

    def test_file_is_private_and_survives_a_restart(self):
        token, _ = self.tokens.issue()
        mode = stat.S_IMODE(os.stat(enrollment_module.TOKENS_FILE).st_mode)
        if os.name == "posix":
            self.assertEqual(mode, 0o600)
        reloaded = enrollment_module.EnrollmentTokens()
        self.assertTrue(reloaded.verify(token))

    def test_expired_and_unknown_tokens_are_rejected(self):
        token, expires = self.tokens.issue(ttl=120)
        with mock.patch("features.nodes.enrollment.time.time", return_value=expires + 1):
            with self.assertRaises(enrollment_module.EnrollmentError):
                self.tokens.verify(token)
        for bad in ("", None, "x" * 43, 12):
            with self.assertRaises(enrollment_module.EnrollmentError):
                self.tokens.verify(bad)

    def test_lifetime_is_clamped_and_active_tokens_are_capped(self):
        _, expires = self.tokens.issue(ttl=10**9)
        self.assertLessEqual(expires - __import__("time").time(), enrollment_module.MAX_TTL + 1)
        for _ in range(enrollment_module.MAX_ACTIVE - 1):
            self.tokens.issue()
        with self.assertRaises(enrollment_module.EnrollmentError) as ctx:
            self.tokens.issue()
        self.assertEqual(ctx.exception.code, "enroll_too_many_tokens")

    def test_corrupted_file_is_reported_and_starts_empty(self):
        enrollment_module.TOKENS_FILE.write_text("{rotto", encoding="utf-8")
        with self.assertLogs("nuxiva.enrollment", level="ERROR"):
            fresh = enrollment_module.EnrollmentTokens()
        self.assertEqual(fresh.active(), 0)


class RouteTest(unittest.TestCase):
    def setUp(self):
        directory = Path(tempfile.mkdtemp())
        patches = [mock.patch.object(enrollment_module, "TOKENS_FILE", directory / "tokens.json"),
                   mock.patch.object(registry_module, "NODES_FILE", directory / "nodes.json")]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.registry = registry_module.Registry()
        self.tokens = enrollment_module.EnrollmentTokens()
        for target, value in (("registry", self.registry), ("tokens", self.tokens)):
            patcher = mock.patch.object(enroll_routes, target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        enroll_routes._failures.clear()
        app = FastAPI()
        app.include_router(enroll_routes.public_routes)
        self.client = TestClient(app)

    def enroll(self, token, node_id="pc-ufficio"):
        return self.client.post("/api/nodes/enroll", json={"token": token, "id": node_id, "name": "Ufficio"})

    def test_valid_token_creates_a_desktop_node_and_is_burned(self):
        token, _ = self.tokens.issue()
        response = self.enroll(token)
        self.assertEqual(response.status_code, 200)
        node = self.registry.authenticate("pc-ufficio", response.json()["token"])
        self.assertEqual(node["type"], "desktop")
        self.assertEqual(self.enroll(token, "pc-altro").status_code, 403)

    def test_unknown_token_is_forbidden_and_rate_limited(self):
        for _ in range(enroll_routes.LIMIT):
            self.assertEqual(self.enroll("sbagliato").json()["detail"], "enroll_token_invalid")
        self.assertEqual(self.enroll("sbagliato").status_code, 429)

    def test_existing_node_is_never_overwritten_and_keeps_the_token_valid(self):
        first, _ = self.tokens.issue()
        self.enroll(first)
        second, _ = self.tokens.issue()
        response = self.enroll(second)
        self.assertEqual((response.status_code, response.json()["detail"]), (409, "enroll_node_exists"))
        self.assertEqual(self.enroll(second, "pc-nuovo").status_code, 200)

    def test_invalid_identifier_does_not_burn_the_token(self):
        token, _ = self.tokens.issue()
        self.assertEqual(self.enroll(token, "A B!").status_code, 400)
        self.assertEqual(self.enroll(token).status_code, 200)

    def test_oversized_and_malformed_bodies_are_refused(self):
        big = self.client.post("/api/nodes/enroll", content=json.dumps({"token": "x" * 5000}),
                               headers={"content-type": "application/json"})
        self.assertEqual(big.status_code, 413)
        self.assertEqual(self.client.post("/api/nodes/enroll", json=[1]).status_code, 400)

    def test_satellites_keep_their_type_but_cannot_claim_to_be_a_server(self):
        for kind, expected in (("satellite", "satellite"), ("display", "display"), ("server", "desktop"), ("<x>", "desktop")):
            token, _ = self.tokens.issue()
            node_id = f"nodo-{expected}-{len(kind)}"
            response = self.client.post("/api/nodes/enroll", json={"token": token, "id": node_id, "name": "Nodo", "type": kind})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.registry.authenticate(node_id, response.json()["token"])["type"], expected)


class SatelliteEnrollmentTest(unittest.TestCase):
    def setUp(self):
        directory = Path(tempfile.mkdtemp())
        self.tokens = enrollment_module.EnrollmentTokens.__new__(enrollment_module.EnrollmentTokens)
        patches = [mock.patch.object(enrollment_module, "TOKENS_FILE", directory / "tokens.json"),
                   mock.patch.object(enroll_routes.trust, "ca_pin", return_value="a" * 64),
                   mock.patch.dict(enroll_routes.secure._active, {"port": 8443})]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.tokens.items = {}
        patcher = mock.patch.object(enroll_routes, "tokens", self.tokens)
        patcher.start()
        self.addCleanup(patcher.stop)
        app = FastAPI()
        app.include_router(enroll_routes.admin_routes)
        app.dependency_overrides[enroll_routes.require_admin] = lambda: "admin"
        self.client = TestClient(app, base_url="https://192.168.1.10")

    def test_admin_downloads_a_single_use_pinned_enrollment(self):
        response = self.client.post("/api/nodes/satellite-enrollment")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        data = response.json()
        self.assertEqual(data["server"], "https://192.168.1.10:8443")
        self.assertEqual(data["pin"], "a" * 64)
        self.assertTrue(self.tokens.verify(data["token"]))

    def test_refused_without_https_or_from_localhost(self):
        with mock.patch.dict(enroll_routes.secure._active, {"port": 0}):
            self.assertEqual(self.client.post("/api/nodes/satellite-enrollment").json()["detail"], "enroll_https_unavailable")
        local = TestClient(self.client.app, base_url="https://127.0.0.1")
        self.assertEqual(local.post("/api/nodes/satellite-enrollment").status_code, 409)


if __name__ == "__main__":
    unittest.main()
