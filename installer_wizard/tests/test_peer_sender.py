import json
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agenti.nodes import peer_envelope, peer_sender
from agenti.nodes.peer_identity import PeerIdentity


class PeerIdentityTest(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "peer.key"

    def test_identity_is_created_private_and_stable(self):
        first = PeerIdentity(self.path)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertRegex(first.public_hex, r"[0-9a-f]{64}")
        self.assertEqual(PeerIdentity(self.path).public_hex, first.public_hex)

    def test_corrupt_identity_is_replaced(self):
        self.path.write_text("zz", encoding="ascii")
        self.assertRegex(PeerIdentity(self.path).public_hex, r"[0-9a-f]{64}")
        self.assertRegex(self.path.read_text(encoding="ascii"), r"[0-9a-f]{64}")

    def test_sealed_locate_verifies_with_the_shared_rules(self):
        identity = PeerIdentity(self.path)
        envelope = identity.seal_locate(["192.168.1.20:8443"])
        self.assertEqual(peer_envelope.verify_locate(envelope, {identity.public_hex}), ["192.168.1.20:8443"])
        with self.assertRaises(ValueError):
            peer_envelope.verify_locate(envelope, {"0" * 64})

    def test_sequence_never_goes_back_even_with_a_frozen_clock(self):
        identity = PeerIdentity(self.path, clock=lambda: 1_700_000_000.0)
        seqs = [identity.seal_locate(["10.0.0.5:7000"])["seq"] for _ in range(5)]
        self.assertEqual(seqs, sorted(set(seqs)))

    def test_invalid_addresses_are_never_signed(self):
        identity = PeerIdentity(self.path)
        for bad in (["0.0.0.0:80"], [], ["x"] * 9, ["10.0.0.1:80", "10.0.0.1:80"]):
            with self.subTest(bad):
                with self.assertRaises(ValueError):
                    identity.seal_locate(bad)


class RecordTest(unittest.TestCase):
    def test_record_fits_a_datagram_and_carries_the_https_port(self):
        identity = PeerIdentity(Path(tempfile.mkdtemp()) / "peer.key")
        with mock.patch.object(peer_sender, "identity", return_value=identity):
            record = peer_sender.build_record(8443, lambda: ["192.168.1.10", "10.0.0.2"])
        self.assertLessEqual(len(record), peer_sender.MAX_DATAGRAM)
        addrs = peer_envelope.verify_locate(json.loads(record), {identity.public_hex})
        self.assertEqual(addrs, ["192.168.1.10:8443", "10.0.0.2:8443"])

    def test_no_address_means_nothing_is_sent(self):
        self.assertIsNone(peer_sender.build_record(8443, lambda: []))

    def test_local_addresses_skip_loopback_and_are_unique(self):
        with mock.patch.object(peer_sender.socket, "getaddrinfo", return_value=[(2, 2, 17, "", ("127.0.0.1", 0)), (2, 2, 17, "", ("192.168.1.5", 0))]):
            found = peer_sender.local_addresses()
        self.assertNotIn("127.0.0.1", found)
        self.assertEqual(len(found), len(set(found)))


if __name__ == "__main__":
    unittest.main()
