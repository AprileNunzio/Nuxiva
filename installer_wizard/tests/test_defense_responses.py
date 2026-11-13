import asyncio
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from access import require_admin
from agenti.firewall import api as firewall_api
from agenti.firewall import model, nft
from agenti.firewall.defense import journal as journal_module
from agenti.firewall.defense import responses
from agenti.firewall.defense.guardian import Guardian
from agenti.firewall.defense.honeypot import honeypot
from agenti.firewall.defense.responder import Refused, Responder
from agenti.firewall.store import store
from tests.test_firewall_runtime import FirewallBase


def run(coro):
    return asyncio.run(coro)


class DefenseBase(FirewallBase):

    def setUp(self):
        super().setUp()
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        patcher = mock.patch.object(journal_module, "JOURNAL", Path(folder.name) / "journal.jsonl")
        patcher.start()
        self.addCleanup(patcher.stop)
        journal_module.journal.recent.clear()
        journal_module.journal.head = "0" * 64
        store.responses.clear()


class ResponseModel(unittest.TestCase):

    def test_targets_are_validated(self):
        self.assertEqual(responses.build("country_block", "country:cn", 60).target, "CN")
        self.assertEqual(responses.build("quarantine", "AA-BB-CC-DD-EE-FF", 5).family, "mac")
        for kind, target in (("tarpit", "aa:bb:cc:dd:ee:ff"), ("country_block", "ZZ"), ("explode", "1.2.3.4"),
                             ("sinkhole", "@gruppo"), ("tarpit", "1.2.3.4; drop")):
            with self.assertRaises(ValueError):
                responses.build(kind, target, 5)

    def test_responses_are_never_permanent(self):
        restored = responses.restore({"kind": "tarpit", "target": "203.0.113.9", "expires": 0})
        self.assertGreater(restored.expires, time.time())

    def test_script_contains_defensive_sets_only_when_enforcing(self):
        answers = [responses.build("tarpit", "203.0.113.9", 10), responses.build("honeypot", "198.51.100.3", 10),
                   responses.build("sinkhole", "2001:db8::9", 10)]
        script = nft.compile_script(model.policy({"mode": "protect"}), [], {}, [], responses=answers,
                                    ranges={"CN": [("1.0.1.0", "1.0.3.255")]})
        for needle in ("set tarpit_4", "203.0.113.9 timeout", "redirect to :47022", "ip6 daddr @sinkhole_6 counter drop",
                       "1.0.1.0-1.0.3.255"):
            self.assertIn(needle, script)
        self.assertNotIn("tarpit", nft.compile_script(model.policy({"mode": "monitor"}), [], {}, [], responses=answers))


class ResponderTests(DefenseBase):

    def test_fail_safes_refuse_dangerous_targets(self):
        responder = Responder()
        responder.seen_admin("8.8.8.8")
        store.policy = model.policy({"trusted": ["192.168.1.50"], "home_countries": ["IT"]})
        for kind, target in (("block", "192.168.1.1"), ("tarpit", "8.8.8.8"), ("quarantine", "192.168.1.50"),
                             ("quarantine", "203.0.113.5"), ("country_block", "IT")):
            with self.assertRaises(Refused, msg=f"{kind} {target}"):
                responder.check(kind, target)
        with mock.patch("agenti.firewall.defense.geo.geo.ranges", return_value=[("8.8.8.0", "8.8.8.255")]), \
                mock.patch("agenti.firewall.defense.geo.geo.lookup", return_value="US"):
            with self.assertRaises(Refused):
                responder.check("country_block", "US")

    def test_execute_records_journal_and_revoke_restores(self):
        responder = Responder()
        store.policy = model.policy({"mode": "protect"})
        run(responder.execute({"kind": "tarpit", "target": "203.0.113.9", "minutes": 15, "reason": "recon_slowdown"}, "auto"))
        self.assertIn("tarpit:203.0.113.9", store.responses)
        self.assertEqual(journal_module.journal.tail(1)[0]["action"], "apply")
        run(responder.revoke("tarpit:203.0.113.9", "nunzio"))
        self.assertEqual(store.responses, {})
        self.assertEqual([e["action"] for e in journal_module.journal.tail()], ["apply", "revoke"])
        self.assertTrue(journal_module.journal.verify())
        with self.assertRaises(Refused):
            run(responder.execute({"kind": "block", "target": "192.168.1.10"}, "auto"))
        self.assertEqual(journal_module.journal.tail(1)[0]["action"], "refused")

    def test_journal_detects_tampering(self):
        journal_module.journal.record(action="apply", kind="tarpit", target="1.2.3.4")
        journal_module.journal.record(action="revoke", kind="tarpit", target="1.2.3.4")
        journal_module.journal.recent[0]["target"] = "5.6.7.8"
        self.assertFalse(journal_module.journal.verify())

    def test_expired_responses_are_pruned(self):
        store.responses["tarpit:203.0.113.9"] = responses.build("tarpit", "203.0.113.9", 1, at=time.time() - 3600)
        self.assertEqual(store.prune(), 1)
        self.assertEqual(store.responses, {})


class GuardianActs(DefenseBase):

    def test_autonomous_guardian_applies_and_strikes(self):
        guardian = Guardian()
        now = time.time()
        store.policy = model.policy({"mode": "protect", "autonomy": "autonomous", "honeypot": True})
        guardian.evaluate([{"kind": "port_scan", "severity": "high", "src": "198.51.100.3", "dst": "192.168.1.10", "count": 40,
                            "at": now}], set(), now)
        with mock.patch.object(honeypot, "start", return_value=True) as started:
            done = run(guardian.act())
        self.assertEqual([(d["kind"], d["target"]) for d in done], [("honeypot", "198.51.100.3")])
        self.assertIn("honeypot:198.51.100.3", store.responses)
        self.assertEqual(guardian.strikes["198.51.100.3"], 1)
        self.assertIn("198.51.100.3", honeypot.allowed)
        started.assert_called_once()
        self.assertFalse(guardian.assessment["actions"])


class RouteTests(DefenseBase):

    def setUp(self):
        super().setUp()
        app = FastAPI()
        app.include_router(firewall_api.admin_routes)
        app.dependency_overrides[require_admin] = lambda: "nunzio"
        self.client = TestClient(app)

    def test_manual_action_revoke_and_journal(self):
        r = self.client.post("/api/firewall/defense/actions", json={"kind": "sinkhole", "target": "203.0.113.50", "minutes": 30})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["responses"][0]["key"], "sinkhole:203.0.113.50")
        r = self.client.delete("/api/firewall/defense/responses/sinkhole:203.0.113.50")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["responses"], [])
        journal = self.client.get("/api/firewall/defense/journal").json()
        self.assertTrue(journal["intact"])
        self.assertEqual(len(journal["entries"]), 2)

    def test_bad_actions_are_refused(self):
        self.assertEqual(self.client.post("/api/firewall/defense/actions", json={"kind": "attack", "target": "1.2.3.4"}).status_code, 400)
        self.assertEqual(self.client.post("/api/firewall/defense/actions", json={"kind": "block", "target": "192.168.1.1"}).status_code, 409)
        self.assertEqual(self.client.delete("/api/firewall/defense/responses/tarpit:9.9.9.9").status_code, 404)


if __name__ == "__main__":
    unittest.main()
