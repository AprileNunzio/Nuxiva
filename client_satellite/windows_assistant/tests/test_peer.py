import json
import socket
import threading
import unittest
from pathlib import Path
from unittest import mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from connection import enroll, peer, peer_envelope, relocate
from connection.client import Client

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = json.loads((ROOT / "native/crates/peer-core/tests/fixtures/locate.json").read_text(encoding="utf-8"))
SERVER_FILE = ROOT / "installer_wizard/agenti/infrastruttura/nodes/peer_envelope.py"


def sealed(seed: bytes, addrs: list[str], seq: int, ts: int) -> bytes:
    key = Ed25519PrivateKey.from_private_bytes(seed)
    from cryptography.hazmat.primitives import serialization
    sender = key.public_key().public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw).hex()
    payload = json.dumps({"type": "locate", "addrs": addrs}, separators=(",", ":"))
    sig = key.sign(peer_envelope.signed_bytes(sender, seq, ts, payload)).hex()
    return json.dumps({"from": sender, "seq": seq, "ts": ts, "ttl": 6, "payload": payload, "sig": sig}).encode()


def sender_of(seed: bytes) -> str:
    return json.loads(sealed(seed, ["10.0.0.5:7000"], 1, 0))["from"]


SEED = bytes(range(32))
NOW = 1_700_000_000.0


class VectorsTest(unittest.TestCase):
    def test_copy_is_identical_to_the_server_verifier(self):
        self.assertEqual((Path(peer_envelope.__file__)).read_bytes(), SERVER_FILE.read_bytes())

    def test_every_shared_case_matches_the_rust_verdict(self):
        trusted = set(FIXTURE["trusted"])
        for case in FIXTURE["cases"]:
            with self.subTest(case["name"]):
                try:
                    peer_envelope.verify_locate(case["envelope"], trusted)
                    got = "ok"
                except ValueError as exc:
                    got = str(exc)
                self.assertEqual(got, case["expect"])


class TrackerTest(unittest.TestCase):
    def setUp(self):
        self.tracker = peer.Tracker(sender_of(SEED), clock=lambda: NOW)

    def record(self, seq=1, ts=int(NOW * 1000), addrs=("192.168.1.20:8443",), seed=SEED):
        return sealed(seed, list(addrs), seq, ts)

    def test_fresh_record_is_accepted_once_per_sequence(self):
        self.assertEqual(self.tracker.accept(self.record(5)), ["192.168.1.20:8443"])
        self.assertIsNone(self.tracker.accept(self.record(5)))
        self.assertIsNone(self.tracker.accept(self.record(4)))
        self.assertEqual(self.tracker.accept(self.record(6)), ["192.168.1.20:8443"])

    def test_stale_future_and_foreign_records_are_dropped(self):
        for raw in (self.record(ts=int(NOW * 1000) - 61_000), self.record(ts=int(NOW * 1000) + 61_000),
                    self.record(seed=bytes(range(1, 33))), b"{", b"\xff\xfe", b"x" * 1300):
            with self.subTest(raw[:20]):
                self.assertIsNone(self.tracker.accept(raw))

    def test_rejected_record_does_not_advance_the_sequence(self):
        self.tracker.accept(self.record(seed=bytes(range(1, 33)), seq=99))
        self.assertEqual(self.tracker.accept(self.record(1)), ["192.168.1.20:8443"])


class ThrottleTest(unittest.TestCase):
    def test_a_source_is_limited_per_window(self):
        clock = [0.0]
        throttle = peer.Throttle(3, 1.0, clock=lambda: clock[0])
        self.assertEqual([throttle.allow("a") for _ in range(5)], [True, True, True, False, False])
        self.assertTrue(throttle.allow("b"))
        clock[0] = 2.0
        self.assertTrue(throttle.allow("a"))

    def test_source_table_is_bounded(self):
        throttle = peer.Throttle(1, 1000.0, clock=lambda: 0.0)
        for i in range(peer.MAX_SOURCES):
            throttle.allow(str(i))
        self.assertFalse(throttle.allow("new"))


class ListenerTest(unittest.TestCase):
    def test_datagram_over_udp_reaches_the_callback(self):
        got, event = [], threading.Event()
        listener = peer.PeerListener(sender_of(SEED), lambda addrs: (got.append(addrs), event.set()), port=0, bind="127.0.0.1")
        listener.tracker.clock = lambda: NOW
        listener.start()
        self.addCleanup(listener.stop)
        self.assertTrue(listener.bound.wait(3))
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(b"garbage", ("127.0.0.1", listener.port))
            sock.sendto(sealed(SEED, ["10.1.2.3:8443"], 1, int(NOW * 1000)), ("127.0.0.1", listener.port))
        self.assertTrue(event.wait(3))
        self.assertEqual(got, [["10.1.2.3:8443"]])


class RelocatorTest(unittest.TestCase):
    def build(self, online=False, probe=lambda url, ca: True):
        client = Client("https://192.168.1.10:8443", "pc-1", "t", "CA")
        cfg = {"server": client.server}
        saved = []
        return client, cfg, saved, relocate.Relocator(client, cfg, lambda: online, lambda c: saved.append(dict(c)), probe)

    def test_moves_to_the_new_address_when_the_server_is_offline(self):
        client, cfg, saved, relocator = self.build()
        self.assertTrue(relocator.offer(["192.168.1.10:8443", "192.168.1.77:8443"]))
        self.assertEqual((client.server, cfg["server"]), ("https://192.168.1.77:8443",) * 2)
        self.assertEqual(saved[-1]["server"], "https://192.168.1.77:8443")

    def test_never_moves_while_the_link_is_healthy(self):
        client, _, saved, relocator = self.build(online=True)
        self.assertFalse(relocator.offer(["192.168.1.77:8443"]))
        self.assertEqual((client.server, saved), ("https://192.168.1.10:8443", []))

    def test_unverified_address_is_skipped(self):
        client, _, saved, relocator = self.build(probe=lambda url, ca: "77" not in url)
        self.assertTrue(relocator.offer(["192.168.1.77:8443", "192.168.1.88:443"]))
        self.assertEqual(client.server, "https://192.168.1.88")

    def test_all_failing_keeps_the_old_address(self):
        client, _, saved, relocator = self.build(probe=lambda url, ca: False)
        self.assertFalse(relocator.offer(["192.168.1.77:8443"]))
        self.assertEqual((client.server, saved), ("https://192.168.1.10:8443", []))

    def test_only_the_first_candidates_are_probed(self):
        probe = mock.Mock(return_value=False)
        _, _, _, relocator = self.build(probe=probe)
        relocator.offer([f"10.0.0.{i}:8443" for i in range(1, 9)])
        self.assertEqual(probe.call_count, relocate.MAX_TRIES)

    def test_url_building(self):
        self.assertEqual(relocate.server_url("10.0.0.1:443"), "https://10.0.0.1")
        self.assertEqual(relocate.server_url("[2001:db8::1]:8443"), "https://[2001:db8::1]:8443")
        self.assertEqual(relocate.server_url("nodo.local:8443"), "https://nodo.local:8443")


class EnrollPeerTest(unittest.TestCase):
    def data(self, **changes):
        import time
        return {"server": "https://192.168.1.10:8443", "token": "T" * 43, "pin": "ab" * 32, "expires": int(time.time()) + 600, **changes}

    def test_peer_is_optional_but_validated(self):
        self.assertEqual(enroll.parse(json.dumps(self.data(peer="cd" * 32)).encode())["peer"], "cd" * 32)
        enroll.parse(json.dumps(self.data()).encode())
        for bad in ("zz", "CD" * 32, 5, "cd" * 31):
            with self.subTest(bad):
                with self.assertRaises(enroll.EnrollError):
                    enroll.parse(json.dumps(self.data(peer=bad)).encode())

    def test_redeem_stores_the_server_id(self):
        cfg = {"name": "pc"}
        with mock.patch.object(enroll.store, "save"), mock.patch.object(Client, "enroll", return_value="tok"):
            enroll.redeem(cfg, self.data(peer="cd" * 32), lambda server: ("ab" * 32, "CA"))
        self.assertEqual(cfg["peer"], "cd" * 32)

    def test_client_reads_the_peer_from_the_server_reply(self):
        client = Client("https://192.168.1.10:8443", "pc", "", "CA")
        with mock.patch.object(Client, "request", return_value={"token": "tok", "peer": "ef" * 32}):
            client.pair("123456", "pc")
        self.assertEqual(client.peer, "ef" * 32)
        with mock.patch.object(Client, "request", return_value={"token": "tok", "peer": "nope"}):
            client.pair("123456", "pc")
        self.assertEqual(client.peer, "")


if __name__ == "__main__":
    unittest.main()
