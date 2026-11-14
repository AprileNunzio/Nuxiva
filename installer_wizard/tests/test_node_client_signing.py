import importlib.util
import json
import time
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

import tests.test_node_trust_api as base
from agenti.medico.vitals import api as vitals_api
from agenti.nodes import api as nodes_api
from agenti.nodes.registry import registry

ROOT = Path(__file__).resolve().parents[2] / "client_satellite"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


declare = load("windows_declare", ROOT / "windows_assistant" / "connection" / "declare.py")
devicekey = load("windows_devicekey", ROOT / "windows_assistant" / "connection" / "devicekey.py")
linux = load("linux_satellite", ROOT / "linux_edge" / "satellite.py")


class ClientSigningTest(unittest.TestCase):
    def setUp(self):
        base.TrustApiTest.setUp(self)
        app = FastAPI()
        app.include_router(nodes_api.public_routes)
        app.include_router(nodes_api.admin_routes)
        app.include_router(vitals_api.public_routes)
        app.dependency_overrides[base.require_admin] = lambda: "admin"
        self.client = TestClient(app)

    def send(self, headers_for, path, payload, bearer=""):
        body = json.dumps(payload).encode()
        headers = {"content-type": "application/json", **headers_for(path, body)}
        if bearer:
            headers["authorization"] = f"Bearer {bearer}"
        return self.client.post(path, content=body, headers=headers)

    def test_windows_client_pairs_with_a_code_and_is_verified_on_every_request(self):
        key = devicekey.DeviceKey.generate()
        node = "pc-windows-uno"
        code = registry.new_code()["code"]
        paired = self.client.post("/api/nodes/pair", json={"code": code, "id": node, "name": "Studio", "type": "desktop",
                                                           "pubkey": key.public_hex()})
        self.assertEqual(paired.status_code, 200, paired.text)
        token = paired.json()["token"]
        self.assertEqual(registry.data["nodes"][node]["pubkey"], key.public_hex())
        sign = lambda path, body: key.sign(node, "POST", path, body, int(time.time()))
        ok = self.send(sign, "/api/nodes/heartbeat", {"version": "1"}, token)
        self.assertEqual(ok.status_code, 200, ok.text)
        stolen = self.client.post("/api/nodes/heartbeat", json={}, headers={"x-nuxiva-node": node,
                                                                            "authorization": f"Bearer {token}"})
        self.assertEqual(stolen.status_code, 401)
        body = json.dumps({"version": "1"}).encode()
        fixed = key.sign_at(node, "POST", "/api/nodes/heartbeat", body, int(time.time()), "a" * 32)
        headers = {"content-type": "application/json", "authorization": f"Bearer {token}", **fixed}
        first = self.client.post("/api/nodes/heartbeat", content=body, headers=headers)
        replay = self.client.post("/api/nodes/heartbeat", content=body, headers=headers)
        self.assertEqual((first.status_code, replay.status_code), (200, 401))
        self.assertEqual(replay.json()["detail"], "node.error.replay")
        query = self.send(sign, "/api/nodes/compute/next?capacity=1", {}, token)
        self.assertNotEqual(query.json().get("detail"), "node.error.signature")

    def test_windows_client_with_a_wrong_clock_gets_a_signature_error_not_a_revocation(self):
        key = devicekey.DeviceKey.generate()
        node = "pc-windows-due"
        code = registry.new_code()["code"]
        token = self.client.post("/api/nodes/pair", json={"code": code, "id": node, "name": "x", "type": "desktop",
                                                          "pubkey": key.public_hex()}).json()["token"]
        late = lambda path, body: key.sign(node, "POST", path, body, int(time.time()) - 3600)
        reply = self.send(late, "/api/nodes/heartbeat", {}, token)
        self.assertEqual((reply.status_code, reply.json()["detail"]), (401, "node.error.clock"))

    def test_linux_client_requests_pairing_with_its_public_key(self):
        seed = "0a" * 32
        node = "linux-uno"
        pub = linux.public_hex(seed)
        submit = self.client.post("/api/nodes/request", json={"id": node, "name": "Rpi", "type": "satellite", "pubkey": pub})
        self.assertEqual(submit.status_code, 200, submit.text)
        self.assertEqual(submit.json()["fingerprint"], devicekey.DeviceKey.from_hex(seed).pairing_code())
        approve = self.client.post(f"/api/nodes/requests/{node}/approve", json={})
        self.assertEqual(approve.status_code, 200, approve.text)
        sign = lambda path, body: linux.proof(seed, node, path, body)
        claim = self.send(sign, "/api/nodes/claim", {"id": node})
        self.assertEqual(claim.status_code, 200, claim.text)
        token = claim.json()["token"]
        beat = self.send(sign, "/api/nodes/heartbeat", {"version": "1"}, token)
        self.assertEqual(beat.status_code, 200, beat.text)

    def test_vitals_node_route_rejects_a_stolen_token(self):
        key = devicekey.DeviceKey.generate()
        node = "pc-windows-tre"
        code = registry.new_code()["code"]
        token = self.client.post("/api/nodes/pair", json={"code": code, "id": node, "name": "x", "type": "desktop",
                                                          "pubkey": key.public_hex()}).json()["token"]
        bare = self.client.post("/api/vitals/node", json={}, headers={"x-nuxiva-node": node,
                                                                        "authorization": f"Bearer {token}"})
        self.assertEqual(bare.status_code, 401)
        sign = lambda path, body: key.sign(node, "POST", path, body, int(time.time()))
        self.assertNotEqual(self.send(sign, "/api/vitals/node", {}, token).status_code, 401)

    def pair_windows(self, node, key):
        code = registry.new_code()["code"]
        reply = self.client.post("/api/nodes/pair", json={"code": code, "id": node, "name": "Studio", "type": "desktop",
                                                          "pubkey": key.public_hex()})
        self.assertEqual(reply.status_code, 200, reply.text)
        return reply.json()["token"]

    def test_repaired_legacy_node_can_become_second_server_with_its_own_announcement(self):
        node = "pc-vecchio"
        code = registry.new_code()["code"]
        self.client.post("/api/nodes/pair", json={"code": code, "id": node, "name": "Vecchio", "type": "desktop"})
        legacy = self.client.put(f"/api/nodes/{node}/trust", json={"profile": "second_server", "allow_second_server": True})
        self.assertEqual(legacy.status_code, 400)
        self.assertEqual(self.client.delete(f"/api/nodes/{node}").status_code, 200)
        key = devicekey.DeviceKey.generate()
        token = self.pair_windows(node, key)
        sign = lambda path, body: key.sign(node, "POST", path, body, int(time.time()))
        facts = declare.local_facts(True)
        report = {"announce": declare.declare({**facts, "cpu_cores": 8, "ram_mb": 16384}, True)}
        self.assertEqual(self.send(sign, "/api/nodes/heartbeat", report, token).status_code, 200)
        upgraded = self.client.put(f"/api/nodes/{node}/trust", json={"profile": "second_server", "allow_second_server": True})
        self.assertEqual((upgraded.status_code, upgraded.json()["mode"]), (200, "second_server"))

    def test_automatic_profile_follows_the_windows_host_flag(self):
        for host_full, expected in ((False, "satellite"), (True, "second_server")):
            node = f"pc-windows-auto-{int(host_full)}"
            key = devicekey.DeviceKey.generate()
            token = self.pair_windows(node, key)
            sign = lambda path, body: key.sign(node, "POST", path, body, int(time.time()))
            facts = {**declare.local_facts(True), "cpu_cores": 8, "ram_mb": 16384}
            self.send(sign, "/api/nodes/heartbeat", {"announce": declare.declare(facts, host_full)}, token)
            self.client.put(f"/api/nodes/{node}/trust", json={"profile": "auto", "allow_second_server": True})
            self.assertEqual(self.client.get(f"/api/nodes/{node}/trust").json()["mode"], expected)
