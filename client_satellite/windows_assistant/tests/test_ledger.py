import json
import tempfile
import unittest
from pathlib import Path

from connection import ledger
from connection.ledger_watch import LedgerWatch

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = json.loads((ROOT / "native/crates/peer-ledger/tests/fixtures/ledger.json").read_text(encoding="utf-8"))
NOW = FIXTURE["now"]
AUTHOR = FIXTURE["trusted"][0]


def fresh() -> ledger.Ledger:
    return ledger.Ledger(FIXTURE["trusted"])


def verdict(book, block) -> str:
    try:
        return "new" if book.accept(block, NOW) else "known"
    except ledger.LedgerError as exc:
        return exc.code


class VectorsTest(unittest.TestCase):
    def test_every_step_matches_the_rust_verdict_and_hash(self):
        book = fresh()
        for step in FIXTURE["steps"]:
            with self.subTest(step["name"]):
                self.assertEqual(verdict(book, step["block"]), step["expect"])
                try:
                    self.assertEqual(ledger.block_hash(step["block"]), step["hash"])
                except (KeyError, TypeError):
                    self.fail("hash")
        self.assertEqual(book.digest(), FIXTURE["heads"])
        self.assertEqual(book.candidates(AUTHOR), FIXTURE["candidates"])

    def test_every_wire_case_matches_the_rust_verdict(self):
        for case in FIXTURE["wires"]:
            with self.subTest(case["name"]):
                try:
                    ledger.decode(case["raw"].encode("utf-8"))
                    got = "ok"
                except ledger.LedgerError as exc:
                    got = exc.code
                self.assertEqual(got, case["expect"])

    def test_delta_for_an_empty_ledger_rebuilds_the_chain(self):
        full = fresh()
        for step in FIXTURE["steps"][:6]:
            verdict(full, step["block"])
        delta = next(c for c in FIXTURE["wires"] if c["name"] == "delta")
        empty = fresh()
        report = empty.absorb(ledger.decode(delta["raw"].encode("utf-8")), NOW)
        self.assertEqual(report, {"applied": 3, "known": 0, "rejected": 0})
        self.assertEqual(empty.digest(), full.digest())
        self.assertEqual(ledger.encode(ledger.decode(delta["raw"].encode("utf-8"))), delta["raw"].encode("utf-8"))


class PersistenceTest(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "ledger.chain"
        self.book = fresh()
        for step in FIXTURE["steps"][:6]:
            verdict(self.book, step["block"])

    def test_round_trip_keeps_every_block(self):
        ledger.save(self.book, self.path)
        self.assertEqual(ledger.load(FIXTURE["trusted"], self.path, NOW).digest(), self.book.digest())

    def test_tampered_file_is_refused(self):
        ledger.save(self.book, self.path)
        self.path.write_bytes(self.path.read_bytes().replace(b"192.168.1.12", b"192.168.1.99"))
        with self.assertRaises(ledger.LedgerError) as caught:
            ledger.load(FIXTURE["trusted"], self.path, NOW)
        self.assertEqual(caught.exception.code, "ledger.error.corrupt")

    def test_missing_file_gives_an_empty_ledger(self):
        self.assertEqual(ledger.load(FIXTURE["trusted"], self.path, NOW).digest(), [])


class FakeClient:
    def __init__(self, reply):
        self.reply, self.sent = reply, []

    def request(self, path, body, **kwargs):
        self.sent.append((path, body))
        return self.reply


class WatchTest(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "ledger.chain"
        full = fresh()
        for step in FIXTURE["steps"][:6]:
            verdict(full, step["block"])
        self.delta = ledger.encode(full.answer(fresh().digest_request())).decode("ascii")

    def watch(self, online, offered, reply=None):
        client = FakeClient({"wire": self.delta} if reply is None else reply)
        return LedgerWatch(client, AUTHOR, self.path, lambda: online, lambda addrs: offered.append(addrs) or True,
                           clock=lambda: NOW / 1000, wait=lambda delay: True), client

    def test_online_sync_absorbs_and_saves(self):
        offered = []
        watch, client = self.watch(True, offered)
        self.assertEqual(watch.step(), 60.0)
        self.assertEqual(client.sent[0][0], "/api/nodes/peer/sync")
        self.assertTrue(self.path.exists())
        self.assertEqual(len(watch.book.digest()), 1)
        self.assertEqual(offered, [])

    def test_offline_offers_saved_addresses(self):
        offered = []
        watch, _ = self.watch(True, offered)
        watch.step()
        watch.is_online = lambda: False
        self.assertEqual(watch.step(), 1.0)
        self.assertEqual(offered[0], watch.book.candidates(AUTHOR))

    def test_forged_reply_changes_nothing(self):
        offered = []
        forged = json.dumps({"t": "delta", "blocks": [{"author": AUTHOR}]})
        watch, _ = self.watch(True, offered, {"wire": forged})
        watch.step()
        self.assertEqual(watch.book.digest(), [])
        self.assertFalse(self.path.exists())

    def test_offline_without_addresses_backs_off(self):
        watch, _ = self.watch(False, [])
        delays = [watch.step() for _ in range(4)]
        self.assertTrue(all(b >= a for a, b in zip(delays, delays[1:])))
        self.assertGreaterEqual(delays[0], 1.0)

    def test_backoff_is_capped(self):
        self.assertLessEqual(ledger.reconnect_delay_ms(99, 7), 75_000)


if __name__ == "__main__":
    unittest.main()
