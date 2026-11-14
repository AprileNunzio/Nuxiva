import hashlib
import json
import secrets
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from access import require_admin
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agenti.nodes import api as nodes_api
from agenti.nodes import audit as audit_module
from agenti.nodes import deviceauth, registry as registry_module, zt_engine
from agenti.nodes.registry import registry
from agenti.nodes.requests import requests as pairing


class Device:
    def __init__(self, node_id="pc-ufficio", seed=3):
        self.id = node_id
        self.key = Ed25519PrivateKey.from_private_bytes(bytes([seed]) * 32)
        self.pub = self.key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
        self.token = ""

    def headers(self, method, path, body=b"", ts=None, nonce=None, bearer=True):
        ts = int(time.time()) if ts is None else ts
        nonce = nonce or secrets.token_hex(16)
        message = zt_engine.canonical(self.id, method, path, ts, nonce, hashlib.sha256(body).hexdigest())
        out = {"x-nuxiva-node": self.id, "x-nuxiva-ts": str(ts), "x-nuxiva-nonce": nonce,
               "x-nuxiva-sig": self.key.sign(message).hex(), "content-type": "application/json"}
        if bearer:
            out["authorization"] = f"Bearer {self.token}"
        return out


class TrustApiTest(unittest.TestCase):
    def setUp(self):
        directory = Path(tempfile.mkdtemp())
        patcher = mock.patch.object(registry_module, "NODES_FILE", directory / "nodes.json")
        patcher.start()
        self.addCleanup(patcher.stop)
        registry.data = {"nodes": {}, "revoked": []}
        registry.pairing = {}
        pairing.pending.clear()
        deviceauth.replay.seen.clear()
        deviceauth._last_reject.clear()
        nodes_api._failures.clear()
        for name, value in (("path", directory / "audit.jsonl"), ("anchor_path", directory / "audit.anchor")):
            patcher = mock.patch.object(audit_module.audit, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.object(audit_module.audit, "entries", [])
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(audit_module.audit, "anchor", "0" * 64)
        patcher.start()
        self.addCleanup(patcher.stop)
        app = FastAPI()
        app.include_router(nodes_api.public_routes)
        app.include_router(nodes_api.admin_routes)
        app.dependency_overrides[require_admin] = lambda: "admin"
        self.client = TestClient(app)
        self.device = Device()

    def post(self, device, path, payload, **kw):
        body = json.dumps(payload).encode()
        return self.client.post(path, content=body, headers=device.headers("POST", path, body, **kw))

    def pair(self, device=None, profile="satellite", allow=False, grants=None):
        device = device or self.device
        submit = self.client.post("/api/nodes/request", json={"id": device.id, "name": "Ufficio", "type": "desktop", "pubkey": device.pub})
        self.assertEqual(submit.status_code, 200, submit.text)
        self.assertTrue(submit.json()["signed"])
        approve = self.client.post(f"/api/nodes/requests/{device.id}/approve",
                                   json={"profile": profile, "allow_second_server": allow, "grants": grants or []})
        self.assertEqual(approve.status_code, 200, approve.text)
        claim = self.post(device, "/api/nodes/claim", {"id": device.id})
        self.assertEqual(claim.status_code, 200, claim.text)
        device.token = claim.json()["token"]
        return device

    def heartbeat(self, device, scopes, cores=8, ram=16384):
        report = {"announce": {"capabilities": [{"scope": s} for s in scopes], "hardware": {"cpu_cores": cores, "ram_mb": ram}}}
        return self.post(device, "/api/nodes/heartbeat", report)

    def trust(self, node_id=None):
        return self.client.get(f"/api/nodes/{node_id or self.device.id}/trust").json()

    def test_pairing_requires_explicit_approval_and_a_signed_claim(self):
        self.client.post("/api/nodes/request", json={"id": self.device.id, "name": "Ufficio", "pubkey": self.device.pub})
        unsigned = self.client.post("/api/nodes/claim", json={"id": self.device.id, "key": "0" * 64})
        self.assertEqual(unsigned.status_code, 401)
        waiting = self.post(self.device, "/api/nodes/claim", {"id": self.device.id})
        self.assertEqual(waiting.json(), {"approved": False})
        pending = self.client.get("/api/nodes").json()["pending"]
        self.assertEqual(len(pending), 1)
        self.assertNotIn("pubkey", pending[0])
        self.assertEqual(len(pending[0]["fingerprint"]), 6)

    def test_a_different_key_cannot_claim_someone_elses_request(self):
        self.client.post("/api/nodes/request", json={"id": self.device.id, "name": "Ufficio", "pubkey": self.device.pub})
        self.client.post(f"/api/nodes/requests/{self.device.id}/approve")
        thief = Device(self.device.id, seed=5)
        self.assertEqual(self.post(thief, "/api/nodes/claim", {"id": self.device.id}).status_code, 401)

    def test_paired_device_defaults_to_satellite_with_limited_scopes(self):
        self.pair()
        self.assertEqual(self.heartbeat(self.device, ["audio.capture", "compute.lease", "fs.read"]).status_code, 200)
        state = self.trust()
        self.assertEqual((state["mode"], state["effective"]), ("satellite", ["audio.capture"]))
        self.assertIn("compute.lease", state["denied"])
        self.assertEqual(self.post(self.device, "/api/nodes/compute/next?capacity=1", {}).status_code, 403)

    def test_second_server_unlocks_compute_after_explicit_approval(self):
        self.pair(profile="second_server", allow=True)
        self.heartbeat(self.device, ["audio.capture", "compute.lease", "node.host_full"])
        self.assertEqual(self.trust()["mode"], "second_server")
        with mock.patch.object(nodes_api.compute_routes.relay, "take", new=mock.AsyncMock(return_value=[])):
            self.assertEqual(self.post(self.device, "/api/nodes/compute/next?capacity=1", {}).status_code, 200)

    def test_changing_profile_later_is_audited_and_reversible(self):
        self.pair()
        self.heartbeat(self.device, ["audio.capture", "compute.lease"])
        path = f"/api/nodes/{self.device.id}/trust"
        upgraded = self.client.put(path, json={"profile": "second_server", "allow_second_server": True})
        self.assertEqual(upgraded.json()["mode"], "second_server")
        refused = self.client.put(path, json={"profile": "second_server", "allow_second_server": False})
        self.assertEqual((refused.status_code, refused.json()["detail"]), (400, "node.error.ceiling_required"))
        self.assertEqual(self.trust()["mode"], "second_server")
        downgraded = self.client.put(path, json={"profile": "satellite", "allow_second_server": False})
        self.assertEqual(downgraded.json()["mode"], "satellite")
        actions = [e["action"] for e in self.client.get("/api/nodes/audit").json()["entries"]]
        self.assertEqual(actions.count("profile.set"), 2)
        self.assertIn("profile.reject", actions)

    def test_unsigned_or_tampered_requests_from_a_keyed_device_are_rejected(self):
        self.pair()
        bearer_only = self.client.post("/api/nodes/heartbeat", json={},
                                       headers={"x-nuxiva-node": self.device.id, "authorization": f"Bearer {self.token()}"})
        self.assertEqual(bearer_only.status_code, 401)
        body = b"{}"
        headers = self.device.headers("POST", "/api/nodes/heartbeat", body)
        tampered = self.client.post("/api/nodes/heartbeat", content=b'{"a":1}', headers=headers)
        self.assertEqual(tampered.status_code, 401)
        stale = self.post(self.device, "/api/nodes/heartbeat", {}, ts=int(time.time()) - 600)
        self.assertEqual(stale.status_code, 401)

    def token(self):
        return self.device.token

    def test_replayed_request_is_rejected(self):
        self.pair()
        body = b"{}"
        headers = self.device.headers("POST", "/api/nodes/heartbeat", body)
        self.assertEqual(self.client.post("/api/nodes/heartbeat", content=body, headers=headers).status_code, 200)
        self.assertEqual(self.client.post("/api/nodes/heartbeat", content=body, headers=headers).status_code, 401)

    def test_stolen_bearer_token_is_useless_without_the_device_key(self):
        self.pair()
        forged = Device(self.device.id, seed=8)
        forged.token = self.device.token
        self.assertEqual(self.post(forged, "/api/nodes/heartbeat", {}).status_code, 401)

    def test_revoked_device_cannot_pair_again_with_the_same_key(self):
        self.pair()
        self.assertEqual(self.client.delete(f"/api/nodes/{self.device.id}").status_code, 200)
        self.assertEqual(self.post(self.device, "/api/nodes/heartbeat", {}).status_code, 401)
        self.client.post("/api/nodes/request", json={"id": self.device.id, "name": "Ufficio", "pubkey": self.device.pub})
        self.assertEqual(self.client.post(f"/api/nodes/requests/{self.device.id}/approve").status_code, 400)
        other = Device(self.device.id, seed=6)
        pairing.pending.clear()
        self.pair(other)
        self.assertIn("node.revoke", [e["action"] for e in self.client.get("/api/nodes/audit").json()["entries"]])

    def test_legacy_device_works_with_bearer_but_can_never_be_second_server(self):
        code = self.client.post("/api/nodes/pairing-code").json()["code"]
        pair = self.client.post("/api/nodes/pair", json={"code": code, "id": "vecchio-nodo", "name": "Vecchio"})
        token = pair.json()["token"]
        headers = {"x-nuxiva-node": "vecchio-nodo", "authorization": f"Bearer {token}"}
        self.assertEqual(self.client.post("/api/nodes/heartbeat", json={}, headers=headers).status_code, 200)
        state = self.trust("vecchio-nodo")
        self.assertTrue(state["legacy"])
        refused = self.client.put("/api/nodes/vecchio-nodo/trust", json={"profile": "second_server", "allow_second_server": True})
        self.assertEqual((refused.status_code, refused.json()["detail"]), (400, "node.error.legacy_identity"))

    def test_forbidden_scopes_are_never_granted_even_if_announced(self):
        self.pair(profile="second_server", allow=True)
        self.heartbeat(self.device, ["admin.users", "vault.read", "audio.capture"])
        state = self.trust()
        self.assertEqual(state["effective"], ["audio.capture"])
        self.assertEqual(sorted(state["rejected"]), ["admin.users", "vault.read"])

    def test_audit_log_endpoint_reports_chain_health(self):
        self.pair()
        report = self.client.get("/api/nodes/audit?limit=5").json()
        self.assertTrue(report["verify"]["ok"])
        self.assertIn("pair.approve", [e["action"] for e in report["entries"]])
        self.assertEqual(self.client.get("/api/nodes/audit?limit=0").status_code, 422)

    def test_listing_never_leaks_keys_or_tokens(self):
        self.pair()
        raw = self.client.get("/api/nodes").text
        self.assertNotIn(self.device.pub, raw)
        self.assertNotIn(self.device.token, raw)
        node = self.client.get("/api/nodes").json()["nodes"][0]
        self.assertEqual(len(node["trust"]["fingerprint"]), 14)
