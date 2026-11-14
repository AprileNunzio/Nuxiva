import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from agenti.nodes import audit as audit_module
from agenti.nodes import esp32_routes
from agenti.nodes.inbox import inbox
from agenti.nodes.registry import registry
from tests.test_node_trust_api import Device, TrustApiTest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import esp32_sign_release as release

VECTORS = json.loads((ROOT / "native" / "crates" / "node-core" / "tests" / "esp32_vectors.json").read_text(encoding="utf-8"))


class RelayTest(unittest.TestCase):
    setUp = TrustApiTest.setUp
    post = TrustApiTest.post
    pair = TrustApiTest.pair
    heartbeat = TrustApiTest.heartbeat

    def paired(self, capabilities=("audio", "relay")):
        self.pair()
        registry.data["nodes"][self.device.id]["type"] = "esp32"
        self.post(self.device, "/api/nodes/heartbeat", {"capabilities": list(capabilities)})
        inbox.take(self.device.id)

    def relay(self, payload, node_id=None):
        return self.client.post(f"/api/nodes/{node_id or self.device.id}/relay", json=payload)

    def test_relay_is_refused_when_the_board_did_not_declare_relays(self):
        self.paired(capabilities=("audio",))
        response = self.relay({"channel": 0, "state": "on"})
        self.assertEqual((response.status_code, response.json()["detail"]), (409, "esp32.relay.unsupported"))
        self.assertEqual(inbox.take(self.device.id), [])

    def test_relay_command_is_queued_for_the_node_and_audited(self):
        self.paired()
        self.assertEqual(self.relay({"channel": 1, "state": "pulse", "ms": 500}).json(), {"queued": True})
        self.assertEqual(inbox.take(self.device.id), [{"type": "relay", "channel": 1, "state": "pulse", "ms": 500}])
        self.assertTrue(any(e.get("action") == "relay" for e in audit_module.audit.entries))

    def test_invalid_commands_never_reach_the_node(self):
        self.paired()
        bad = [{"channel": 8, "state": "on"}, {"channel": -1, "state": "on"}, {"channel": "1", "state": "on"},
               {"channel": True, "state": "on"}, {"channel": 0, "state": "toggle"}, {"channel": 0, "state": "pulse"},
               {"channel": 0, "state": "pulse", "ms": 10}, {"channel": 0, "state": "pulse", "ms": 10 ** 6},
               {"channel": 0, "state": "on", "ms": -1}, {"channel": 0, "state": "on", "ms": 10 ** 9}, {}]
        for payload in bad:
            self.assertEqual(self.relay(payload).status_code, 400, payload)
        self.assertEqual(self.client.post(f"/api/nodes/{self.device.id}/relay", json=[1]).status_code, 400)
        self.assertEqual(inbox.take(self.device.id), [])

    def test_only_esp32_nodes_accept_relay_commands(self):
        self.paired()
        registry.data["nodes"][self.device.id]["type"] = "desktop"
        self.assertEqual(self.relay({"channel": 0, "state": "on"}).status_code, 404)
        self.assertEqual(self.relay({"channel": 0, "state": "on"}, "nessuno").status_code, 404)

    def test_relay_action_normalises_valid_input(self):
        self.assertEqual(esp32_routes.relay_action({"channel": 0, "state": "off"}), {"type": "relay", "channel": 0, "state": "off"})
        self.assertEqual(esp32_routes.relay_action({"channel": 7, "state": "on", "ms": 0})["ms"], 0)


class FirmwareTest(unittest.TestCase):
    setUp = TrustApiTest.setUp
    post = TrustApiTest.post
    pair = TrustApiTest.pair

    def prepare(self):
        self.pair()
        self.firmware = Path(tempfile.mkdtemp())
        patcher = mock.patch.object(esp32_routes, "FIRMWARE_DIR", self.firmware)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.key = release.load_key("5a" * 32)
        self.image = bytes((i * 7 + 3) & 0xFF for i in range(5000))
        manifest = release.sign(self.image, "1.2.0", self.key)
        (self.firmware / "manifest.json").write_text(json.dumps(manifest), encoding="ascii")
        (self.firmware / "image.bin").write_bytes(self.image)
        return manifest

    def test_authenticated_node_gets_the_signed_manifest_and_image(self):
        manifest = self.prepare()
        served = self.post(self.device, "/api/nodes/firmware/esp32/manifest", {})
        self.assertEqual(served.status_code, 200)
        self.assertEqual(served.json(), manifest)
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(release.public_hex(self.key))).verify(
            bytes.fromhex(served.json()["sig"]), release.message("1.2.0", len(self.image), hashlib.sha256(self.image).hexdigest()))
        image = self.post(self.device, "/api/nodes/firmware/esp32/image", {})
        self.assertEqual(image.content, self.image)

    def test_anonymous_and_unsigned_requests_are_refused(self):
        self.prepare()
        self.assertEqual(self.client.post("/api/nodes/firmware/esp32/manifest", json={}).status_code, 401)
        self.assertEqual(self.client.post("/api/nodes/firmware/esp32/image", json={}).status_code, 401)

    def test_missing_or_tampered_firmware_is_never_served(self):
        self.prepare()
        (self.firmware / "image.bin").write_bytes(self.image[:-1] + b"\x00")
        self.assertEqual(self.post(self.device, "/api/nodes/firmware/esp32/image", {}).status_code, 409)
        (self.firmware / "image.bin").unlink()
        self.assertEqual(self.post(self.device, "/api/nodes/firmware/esp32/manifest", {}).status_code, 404)


class ReleaseSigningTest(unittest.TestCase):
    def test_signature_matches_the_shared_vector(self):
        vector = VECTORS["manifest"]
        key = release.load_key(vector["seed"])
        image = bytes((i * 7 + 3) & 0xFF for i in range(5000))
        self.assertEqual(release.public_hex(key), vector["public"])
        signed = release.sign(image, vector["version"], key)
        self.assertEqual(signed, {k: vector[k] for k in ("version", "size", "sha256", "sig")})

    def test_inputs_are_validated(self):
        key = release.load_key("5a" * 32)
        for version in ("1.2", "a.b.c", "1.2.3.4", ""):
            with self.assertRaises(ValueError):
                release.sign(b"x", version, key)
        with self.assertRaises(ValueError):
            release.sign(b"", "1.0.0", key)
        with self.assertRaises(ValueError):
            release.sign(b"x" * (release.MAX_BYTES + 1), "1.0.0", key)
        for seed in ("zz", "5A" * 32, "5a" * 31):
            with self.assertRaises(ValueError):
                release.load_key(seed)


if __name__ == "__main__":
    unittest.main()
