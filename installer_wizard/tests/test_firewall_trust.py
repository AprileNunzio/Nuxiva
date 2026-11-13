import subprocess
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from access import require_admin
from agenti.firewall.defense import journal as journal_module
from agenti.firewall.defense import trust as trust_module
from agenti.firewall import api as firewall_api
from agenti.firewall import model, nft
from agenti.firewall.store import store
from tests.test_firewall_runtime import FirewallBase


class TrustTests(FirewallBase):

    def setUp(self):
        super().setUp()
        app = FastAPI()
        app.include_router(firewall_api.admin_routes)
        app.dependency_overrides[require_admin] = lambda: "nunzio"
        self.client = TestClient(app)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        for target, name, value in ((trust_module, "META_FILE", Path(folder.name) / "trust.json"),
                                    (journal_module, "JOURNAL", Path(folder.name) / "journal.jsonl")):
            patcher = mock.patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        trust_module.trust.meta.clear()
        trust_module.trust.pending.clear()

    def trust(self, address, accept_risks=False):
        r = self.client.post("/api/firewall/trusted/requests", json={"address": address, "label": "telefono"})
        if r.status_code != 200:
            return r
        body = r.json()
        return self.client.post(f"/api/firewall/trusted/requests/{body['id']}/confirm",
                                json={"code": body["code"], "accept_risks": accept_risks})

    def test_device_can_be_trusted_and_untrusted(self):
        self.assertEqual(self.client.put("/api/firewall/trusted", json={"address": "192.168.1.50", "trusted": True}).status_code, 428)
        r = self.trust("192.168.1.50")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("192.168.1.50", r.json()["policy"]["trusted"])
        r = self.client.put("/api/firewall/trusted", json={"address": "192.168.1.50", "trusted": False})
        self.assertNotIn("192.168.1.50", r.json()["policy"]["trusted"])

    def test_trusting_lifts_an_existing_block(self):
        self.client.post("/api/firewall/blocks", json={"address": "192.168.1.60", "minutes": 0})
        self.assertIn("192.168.1.60", store.blocks)
        self.trust("192.168.1.60")
        self.assertNotIn("192.168.1.60", store.blocks)

    def test_trusted_server_and_router_cannot_be_blocked(self):
        self.trust("192.168.1.50")
        for address in ("192.168.1.50", "192.168.1.10", "192.168.1.1"):
            r = self.client.post("/api/firewall/blocks", json={"address": address, "minutes": 10})
            self.assertEqual(r.status_code, 400, address)
        self.assertEqual(store.blocks, {})

    def test_groups_and_garbage_cannot_be_trusted(self):
        for bad in ("@ufficio", "non-un-indirizzo", ""):
            r = self.trust(bad)
            self.assertEqual(r.status_code, 400, bad)

    def test_confirmation_needs_the_right_code_and_risk_acknowledgement(self):
        body = self.client.post("/api/firewall/trusted/requests", json={"address": "192.168.1.70"}).json()
        r = self.client.post(f"/api/firewall/trusted/requests/{body['id']}/confirm", json={"code": "000000" if body["code"] != "000000" else "111111"})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(self.trust("8.8.8.8").status_code, 409)
        self.assertEqual(self.trust("8.8.8.8", accept_risks=True).status_code, 200)
        self.assertEqual(self.trust("10.0.0.0/8").status_code, 409)

    def test_voice_tools_trust_only_single_home_devices(self):
        import asyncio
        from agenti.firewall import tools
        self.assertIn("affidabile", asyncio.run(tools.firewall_trust("192.168.1.90", "tablet")))
        self.assertIn("tablet", asyncio.run(tools.firewall_trusted()))
        with self.assertRaises(ValueError):
            asyncio.run(tools.firewall_trust("8.8.8.8"))
        asyncio.run(tools.firewall_untrust("192.168.1.90"))
        self.assertEqual(store.policy.trusted, [])

    def test_revocation_and_listing(self):
        self.trust("192.168.1.80")
        devices = self.client.get("/api/firewall/trusted").json()["devices"]
        self.assertEqual([(d["address"], d["label"]) for d in devices], [("192.168.1.80", "telefono")])
        r = self.client.delete("/api/firewall/trusted/192.168.1.80")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["devices"], [])


@unittest.skipUnless(shutil.which("nft"), "nft assente")
class HardeningSyntaxTests(unittest.TestCase):

    def test_generated_script_is_accepted_by_nftables(self):
        for mode in ("protect", "lockdown"):
            script = nft.compile_script(model.Policy(mode=mode, trusted=[model.address("192.168.1.50")]), [], {}, [])
            self.assertIn("tcp flags syn limit rate over", script)
            with tempfile.TemporaryDirectory() as root:
                path = Path(root) / "g.nft"
                path.write_text(script, encoding="utf-8")
                check = subprocess.run(["nft", "-c", "-f", str(path)], capture_output=True, text=True)
            if "Operation not permitted" in check.stderr:
                self.skipTest("privilegi insufficienti per controllare nftables")
            self.assertEqual(check.returncode, 0, check.stderr)


if __name__ == "__main__":
    unittest.main()
