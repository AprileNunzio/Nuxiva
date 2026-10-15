import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
for p in (str(_ROOT), str(_ROOT / "installer_wizard"), str(_ROOT / "installer_wizard" / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("NUXIVA_STATE_DIR", tempfile.mkdtemp())

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import auth
import mesh_api
import mesh_topology
import node_api
import update_api
from server.features.mesh_coordinator.p2p_mesh import p2p_mesh


def _admin_app() -> FastAPI:
    app = FastAPI()
    for module in (mesh_api, node_api, update_api):
        app.include_router(module.admin_routes)
    app.dependency_overrides[mesh_topology.paired_nodes] = lambda: []
    app.dependency_overrides[mesh_topology.paired_source] = lambda: (lambda: [])
    return app


class ConsoleSecurityTests(unittest.TestCase):
    def setUp(self):
        self.anon = TestClient(_admin_app())
        self.admin = TestClient(_admin_app())
        self.admin.cookies.set(auth.SESSION_COOKIE, auth.issue("root"))

    def test_v5_routes_require_session(self):
        for path in ("/api/v5/mesh/topology", "/api/v5/nodes", "/api/v5/updater/status"):
            self.assertEqual(self.anon.get(path).status_code, 401, path)
        self.assertEqual(self.admin.get("/api/v5/mesh/topology").status_code, 200)

    def test_mutations_require_csrf_header(self):
        path = f"/api/v5/nodes/{p2p_mesh.node_id}/name"
        self.assertEqual(self.admin.patch(path, json={"name": "Casa"}).status_code, 403)
        ok = self.admin.patch(path, json={"name": "Casa"}, headers={"X-Nuxiva-Request": "1"})
        self.assertEqual(ok.status_code, 200)

    def test_forged_session_cookie_is_rejected(self):
        forged = TestClient(_admin_app())
        forged.cookies.set(auth.SESSION_COOKIE, "cm9vdHxub3RhbnVtYmVyfGZha2U=")
        self.assertEqual(forged.get("/api/v5/mesh/topology").status_code, 401)

    def test_websocket_requires_session_and_same_origin(self):
        for client, origin in ((self.anon, "http://testserver"), (self.admin, "http://evil.example"), (self.admin, None)):
            headers = {"origin": origin} if origin else {}
            with self.assertRaises(WebSocketDisconnect):
                with client.websocket_connect("/api/v5/mesh/telemetry/stream", headers=headers) as ws:
                    ws.receive_json()
        with self.admin.websocket_connect("/api/v5/mesh/telemetry/stream", headers={"origin": "http://testserver"}) as ws:
            self.assertIn("nodes", ws.receive_json())

    def test_public_peer_routes_require_paired_token(self):
        public = FastAPI()
        public.include_router(mesh_api.public_routes)

        def reject():
            raise HTTPException(status_code=401, detail="node_unauthorized")

        public.dependency_overrides[mesh_api._require_paired_node] = reject
        client = TestClient(public)
        self.assertEqual(client.post("/api/v5/mesh/crdt/merge", json={}).status_code, 401)
        self.assertEqual(client.get("/api/v5/mesh/topology").status_code, 404)


class TopologyCompositionTests(unittest.TestCase):
    def test_paired_nodes_are_merged_with_real_metrics(self):
        paired = [{
            "id": "sat-cucina", "name": "Cucina", "type": "satellite", "type_label": "Satellite audio",
            "ip": "192.168.1.50", "online": True, "room": "Cucina", "last_seen": time.time(),
            "metrics": {"cpu": 12.5, "ram": 50.0, "temp": 48.2, "uptime": 3600},
            "hardware": {"cores": 4, "ram_gb": 8.0, "gpu": "", "os": "Debian 12"},
        }]
        state = mesh_topology.compose_topology(p2p_mesh, paired)
        node = next(n for n in state["nodes"] if n["id"] == "sat-cucina")
        self.assertEqual(node["parent_id"], p2p_mesh.node_id)
        self.assertEqual(node["telemetry"]["ram_used_gb"], 4.0)
        self.assertEqual(node["telemetry"]["cpu_percent"], 12.5)
        self.assertIsNone(node["telemetry"]["gpu_name"])
        self.assertTrue(node["online"])
        local = next(n for n in state["nodes"] if n["id"] == p2p_mesh.node_id)
        self.assertEqual(local["source"], "local")


if __name__ == "__main__":
    unittest.main()
