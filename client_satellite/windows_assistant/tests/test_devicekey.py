import json
import time
import unittest
from pathlib import Path
from unittest import mock

from connection import client as link
from connection.devicekey import DeviceKey, DeviceKeyError

VECTORS = Path(__file__).resolve().parents[3] / "native" / "crates" / "node-core" / "tests" / "signer_vectors.json"


class ParityTest(unittest.TestCase):
    def test_signature_matches_the_rust_vector(self):
        vector = json.loads(VECTORS.read_text(encoding="utf-8"))
        key = DeviceKey.from_hex(vector["seed"])
        headers = key.sign_at(vector["node"], vector["method"], vector["path"], vector["body"].encode(), vector["ts"],
                              vector["nonce"])
        self.assertEqual(key.public_hex(), vector["public"])
        self.assertEqual(headers["X-Nuxiva-Sig"], vector["signature"])

    def test_pairing_code_has_six_digits_and_is_stable(self):
        key = DeviceKey.from_hex("07" * 32)
        self.assertRegex(key.pairing_code(), r"^\d{6}$")
        self.assertEqual(key.pairing_code(), DeviceKey.from_hex("07" * 32).pairing_code())


class KeyTest(unittest.TestCase):
    def test_invalid_seeds_are_rejected(self):
        for bad in ("zz", "00" * 31, "AB" * 32, "", None, 7):
            if bad in ("", None):
                self.assertIsNone(DeviceKey.load(bad or ""))
                continue
            with self.assertRaises(DeviceKeyError):
                DeviceKey.from_hex(bad)

    def test_generated_keys_are_unique_and_roundtrip(self):
        a, b = DeviceKey.generate(), DeviceKey.generate()
        self.assertNotEqual(a.seed_hex(), b.seed_hex())
        self.assertEqual(DeviceKey.from_hex(a.seed_hex()).public_hex(), a.public_hex())

    def test_nonces_never_repeat(self):
        key = DeviceKey.generate()
        nonces = {key.sign("pc-uno", "POST", "/a", b"", 1)["X-Nuxiva-Nonce"] for _ in range(200)}
        self.assertEqual(len(nonces), 200)


class FakeResponse:
    def __init__(self, status=200, body=b"{}"):
        self.status, self._body = status, body

    def read(self, *_):
        return self._body


class ClientTest(unittest.TestCase):
    def call(self, key, response=None, **kwargs):
        conn = mock.MagicMock()
        conn.getresponse.return_value = response or FakeResponse()
        with mock.patch.object(link.http.client, "HTTPSConnection", return_value=conn), \
                mock.patch.object(link.tls, "pinned_context"):
            client = link.Client("https://10.0.0.2:8443", "pc-uno", "tok", "pem", key)
            client.request("/api/nodes/heartbeat", {"a": 1}, **kwargs)
        return conn.request.call_args

    def test_signed_client_binds_body_and_path(self):
        key = DeviceKey.generate()
        call = self.call(key)
        headers, payload = call.args[3], call.args[2]
        self.assertEqual(headers["X-Nuxiva-Node"], "pc-uno")
        self.assertLessEqual(abs(int(headers["X-Nuxiva-Ts"]) - time.time()), 5)
        again = key.sign_at("pc-uno", "POST", "/api/nodes/heartbeat", payload, int(headers["X-Nuxiva-Ts"]),
                            headers["X-Nuxiva-Nonce"])
        self.assertEqual(again["X-Nuxiva-Sig"], headers["X-Nuxiva-Sig"])

    def test_legacy_client_sends_only_the_bearer_token(self):
        headers = self.call(None).args[3]
        self.assertNotIn("X-Nuxiva-Sig", headers)
        self.assertEqual(headers["Authorization"], "Bearer tok")

    def test_signature_errors_are_not_revocations(self):
        body = json.dumps({"detail": "node.error.clock"}).encode()
        with self.assertRaises(link.SignatureRejected):
            self.call(DeviceKey.generate(), FakeResponse(401, body))
        with self.assertRaises(link.Unauthorized):
            self.call(DeviceKey.generate(), FakeResponse(401, b'{"detail":"Nodo non autorizzato"}'))

    def test_pairing_sends_the_public_key(self):
        key = DeviceKey.generate()
        conn = mock.MagicMock()
        conn.getresponse.return_value = FakeResponse(200, b'{"token":"abc"}')
        with mock.patch.object(link.http.client, "HTTPSConnection", return_value=conn), mock.patch.object(link.tls, "pinned_context"):
            token = link.Client("https://10.0.0.2:8443", "pc-uno", "", "pem", key).pair("123456", "Studio")
        sent = json.loads(conn.request.call_args.args[2])
        self.assertEqual(token, "abc")
        self.assertEqual(sent["pubkey"], key.public_hex())


if __name__ == "__main__":
    unittest.main()
