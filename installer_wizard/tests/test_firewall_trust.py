import subprocess
import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from access import require_admin
from features.firewall import api as firewall_api
from features.firewall import model, nft
from features.firewall.store import store
from tests.test_firewall_runtime import FirewallBase


class TrustTests(FirewallBase):

    def setUp(self):
        super().setUp()
        app = FastAPI()
        app.include_router(firewall_api.admin_routes)
        app.dependency_overrides[require_admin] = lambda: "nunzio"
        self.client = TestClient(app)

    def test_device_can_be_trusted_and_untrusted(self):
        r = self.client.put("/api/firewall/trusted", json={"address": "192.168.1.50", "trusted": True})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("192.168.1.50", r.json()["policy"]["trusted"])
        r = self.client.put("/api/firewall/trusted", json={"address": "192.168.1.50", "trusted": False})
        self.assertNotIn("192.168.1.50", r.json()["policy"]["trusted"])

    def test_trusting_lifts_an_existing_block(self):
        self.client.post("/api/firewall/blocks", json={"address": "192.168.1.60", "minutes": 0})
        self.assertIn("192.168.1.60", store.blocks)
        self.client.put("/api/firewall/trusted", json={"address": "192.168.1.60", "trusted": True})
        self.assertNotIn("192.168.1.60", store.blocks)

    def test_trusted_server_and_router_cannot_be_blocked(self):
        self.client.put("/api/firewall/trusted", json={"address": "192.168.1.50", "trusted": True})
        for address in ("192.168.1.50", "192.168.1.10", "192.168.1.1"):
            r = self.client.post("/api/firewall/blocks", json={"address": address, "minutes": 10})
            self.assertEqual(r.status_code, 400, address)
        self.assertEqual(store.blocks, {})

    def test_groups_and_garbage_cannot_be_trusted(self):
        for bad in ("@ufficio", "non-un-indirizzo", ""):
            r = self.client.put("/api/firewall/trusted", json={"address": bad, "trusted": True})
            self.assertEqual(r.status_code, 400, bad)


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
