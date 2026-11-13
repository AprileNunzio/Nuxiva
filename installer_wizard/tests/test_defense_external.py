import asyncio
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from agenti.capabilities import audit, mcp, tokens
from agenti.firewall import api as firewall_api
from agenti.firewall import model, tools
from agenti.firewall.defense import journal as journal_module
from agenti.firewall.defense.guardian import guardian
from agenti.firewall.store import store
from tests.test_firewall_runtime import FirewallBase


class ExternalTests(FirewallBase):

    def setUp(self):
        super().setUp()
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        for target, name, value in ((tokens, "FILE", Path(folder.name) / "tokens.json"),
                                    (journal_module, "JOURNAL", Path(folder.name) / "journal.jsonl")):
            patcher = mock.patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        tokens.FAILS.clear()
        audit.CALLS.clear()
        app = FastAPI()
        app.include_router(firewall_api.admin_routes)
        self.client = TestClient(app)
        now = time.time()
        store.policy = model.policy({"mode": "protect"})
        guardian.evaluate([{"kind": "brute_force", "severity": "high", "src": "198.51.100.7", "dst": "192.168.1.10", "count": 9, "at": now}],
                          set(), now)

    def headers(self, scope):
        return {"Authorization": "Bearer " + tokens.create("monitor", False, "operator", scope)["token"]}

    def test_scoped_token_reads_only_what_it_was_given(self):
        h = self.headers(["firewall_incidents"])
        r = self.client.get("/api/firewall/external/incidents", headers=h)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["incidents"][0]["source"], "198.51.100.7")
        self.assertEqual(self.client.get("/api/firewall/external/state", headers=h).status_code, 403)
        self.assertEqual(self.client.get("/api/firewall/external/nope", headers=h).status_code, 404)

    def test_state_hides_details(self):
        r = self.client.get("/api/firewall/external/state", headers=self.headers(["firewall_defense"]))
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("incidents", r.json())
        self.assertNotIn("journal", r.json())

    def test_missing_wrong_or_unscoped_tokens_are_refused(self):
        self.assertEqual(self.client.get("/api/firewall/external/state").status_code, 401)
        self.assertEqual(self.client.get("/api/firewall/external/state", headers={"Authorization": "Bearer jv_x"}).status_code, 401)
        unscoped = {"Authorization": "Bearer " + tokens.create("all", False, "operator", None)["token"]}
        self.assertEqual(self.client.get("/api/firewall/external/state", headers=unscoped).status_code, 403)
        hostile = {**self.headers(["firewall_defense"]), "Origin": "https://evil.example"}
        self.assertEqual(self.client.get("/api/firewall/external/state", headers=hostile).status_code, 403)

    def test_rate_limit_and_audit(self):
        h = self.headers(["firewall_defense"])
        with mock.patch.object(audit, "LIMIT", 2):
            codes = [self.client.get("/api/firewall/external/state", headers=h).status_code for _ in range(3)]
        self.assertEqual(codes, [200, 200, 429])
        self.assertEqual(audit.recent(1)[0]["tool"], "firewall_defense")

    def test_mcp_exposes_read_tools_only_with_explicit_scope(self):
        plain = {"id": "a", "label": "x", "risky": False, "role": "operator", "allowed_tools": None}
        scoped = {**plain, "allowed_tools": ["firewall_status", "firewall_incidents", "firewall_defend", "firewall_block"]}
        self.assertFalse({"firewall_status", "firewall_incidents"} & set(mcp.visible(plain)))
        self.assertEqual(sorted(set(mcp.visible(scoped)) & {"firewall_status", "firewall_incidents", "firewall_defend", "firewall_block"}),
                         ["firewall_incidents", "firewall_status"])

    def test_defend_tool_goes_through_fail_safes(self):
        self.assertIn("revocabile", asyncio.run(tools.firewall_defend("tarpit", "203.0.113.9", 15)))
        self.assertIn("tarpit:203.0.113.9", store.responses)
        self.assertIn("revocata", asyncio.run(tools.firewall_defense_revoke("tarpit:203.0.113.9")))
        with self.assertRaises(ValueError):
            asyncio.run(tools.firewall_defend("block", "192.168.1.1", 15))
        with self.assertRaises(ValueError):
            asyncio.run(tools.firewall_defend("explode", "1.2.3.4"))
        self.assertIn("incidenti", asyncio.run(tools.firewall_incidents()))


if __name__ == "__main__":
    unittest.main()
