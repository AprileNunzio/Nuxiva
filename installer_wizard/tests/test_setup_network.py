import unittest
from unittest import mock
from fastapi.testclient import TestClient

import nuxiva_supervisor
import setup_api
import setup_network


class SetupNetworkTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.public = TestClient(nuxiva_supervisor.public)
        self.done_patch = mock.patch.object(setup_api, "done", return_value=False)
        self.private_patch = mock.patch.object(setup_api, "_private_client", lambda r: True)
        self.local_patch = mock.patch.object(setup_api, "is_local", lambda r: True)
        self.done_patch.start()
        self.private_patch.start()
        self.local_patch.start()
        offline = mock.patch.object(setup_network, "_get_public_ip_and_ping", return_value=("203.0.113.7", 12.5))
        offline.start()
        self.addCleanup(offline.stop)

    def tearDown(self):
        self.local_patch.stop()
        self.private_patch.stop()
        self.done_patch.stop()

    async def test_diagnostics_structure(self):
        diag = await setup_network.get_network_diagnostics()
        self.assertIn("local_ip", diag)
        self.assertIn("public_ip", diag)
        self.assertIn("ping_ms", diag)
        self.assertIn("dns", diag)
        self.assertIn("traffic", diag)
        self.assertIn("interfaces", diag)
        self.assertIn("bytes_sent_fmt", diag["traffic"])
        self.assertIn("bytes_recv_fmt", diag["traffic"])

    def test_endpoint_returns_json(self):
        res = self.public.get("/api/setup/network")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("local_ip", data)
        self.assertIn("traffic", data)
        self.assertIn("interfaces", data)
