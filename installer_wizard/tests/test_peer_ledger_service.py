import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agenti.nodes import peer_ledger


class FakeLedger:
    def __init__(self, seed):
        self.seed, self.enrolled, self.saved, self.last = seed, [], [], None

    def load(self, path, now):
        raise ValueError("corrotto")

    def enroll(self, peer):
        if len(peer) != 64:
            raise ValueError("id")
        self.enrolled.append(peer)

    def announce(self, addrs, now):
        changed = addrs != self.last
        self.last = addrs
        return changed

    def save(self, path):
        self.saved.append(path)

    def candidates(self, peer):
        return ["10.0.0.2:8443"]

    def handle(self, wire, now):
        if wire == "bad":
            raise ValueError("wire")
        return "reply:" + wire

    def digest_request(self):
        return "digest"


class _Identity:
    def seed_hex(self):
        return "ab" * 32


def service(path):
    return peer_ledger.PeerLedgerService(path, clock=lambda: 1_700_000_000.0)


class PeerLedgerServiceTest(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "ledger.chain"
        self.identity = mock.patch.object(peer_ledger, "identity", lambda: _Identity())
        self.identity.start()
        self.addCleanup(self.identity.stop)

    def test_without_native_module_everything_degrades_quietly(self):
        with mock.patch.object(peer_ledger.native_core, "symbol", return_value=None):
            svc = service(self.path)
            self.assertFalse(svc.available)
            self.assertFalse(svc.announce(["10.0.0.1:1"]))
            self.assertEqual(svc.candidates("a" * 64), [])
            self.assertIsNone(svc.handle("x"))
            self.assertIsNone(svc.digest())
            self.assertFalse(svc.enroll("a" * 64))

    def test_announce_persists_only_when_changed(self):
        with mock.patch.object(peer_ledger.native_core, "symbol", return_value=FakeLedger):
            svc = service(self.path)
            self.assertTrue(svc.announce(["10.0.0.1:1"]))
            self.assertFalse(svc.announce(["10.0.0.1:1"]))
            self.assertEqual(len(svc._inner.saved), 1)

    def test_corrupt_file_does_not_block_start(self):
        self.path.write_text("x")
        with mock.patch.object(peer_ledger.native_core, "symbol", return_value=FakeLedger):
            self.assertTrue(service(self.path).available)

    def test_invalid_input_is_rejected(self):
        with mock.patch.object(peer_ledger.native_core, "symbol", return_value=FakeLedger):
            svc = service(self.path)
            self.assertFalse(svc.enroll("short"))
            self.assertTrue(svc.enroll("a" * 64))
            self.assertIsNone(svc.handle("bad"))
            self.assertIsNone(svc.handle("x" * (peer_ledger.MAX_WIRE + 1)))
            self.assertEqual(svc.handle("ok"), "reply:ok")
            self.assertEqual(svc.digest(), "digest")


if __name__ == "__main__":
    unittest.main()
