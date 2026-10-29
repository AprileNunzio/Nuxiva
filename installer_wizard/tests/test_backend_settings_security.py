import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException
from fastapi.testclient import TestClient

import access
import nuxiva_supervisor
import system_api

HEADERS = {"X-Nuxiva-Request": "1"}


class BackendSettingsSecurityTest(unittest.TestCase):
    def setUp(self):
        self.local = False
        self.written = []
        for patch in (mock.patch.object(access, "is_local", lambda request: self.local),
                      mock.patch.object(system_api, "NUXIVA_DIR", Path(tempfile.mkdtemp())),
                      mock.patch.object(system_api, "write_env", self.written.append)):
            patch.start()
            self.addCleanup(patch.stop)
        self.public = TestClient(nuxiva_supervisor.public)
        self.admin = TestClient(nuxiva_supervisor.admin)
        self.admin.post("/api/auth/login", json={"username": "admin", "password": "nuxiva"}, headers=HEADERS)

    def test_public_port_cannot_change_backend_settings(self):
        self.local = True
        r = self.public.post("/api/system/backend-settings", json={"ollama_url": "http://evil.example:11434"}, headers=HEADERS)
        self.assertIn(r.status_code, (404, 405))
        self.assertEqual(self.written, [])

    def test_public_read_needs_the_display(self):
        self.assertEqual(self.public.get("/api/system/backend-settings").status_code, 401)
        self.local = True
        self.assertEqual(self.public.get("/api/system/backend-settings").status_code, 200)

    def test_admin_routes_require_login_and_csrf_header(self):
        anon = TestClient(nuxiva_supervisor.admin)
        self.assertEqual(anon.get("/api/system/backend-settings").status_code, 401)
        self.assertEqual(anon.post("/api/system/backend-settings", json={}, headers=HEADERS).status_code, 401)
        self.assertEqual(anon.post("/api/system/display-settings", json={}, headers=HEADERS).status_code, 401)
        self.assertEqual(self.admin.post("/api/system/backend-settings", json={"mesh_broadcast": False}).status_code, 403)
        ok = self.admin.post("/api/system/backend-settings", json={"ollama_url": "192.168.1.50", "active_llm_model": "qwen3:8b"}, headers=HEADERS)
        self.assertEqual(ok.status_code, 200, ok.text)
        self.assertEqual(ok.json()["settings"]["ollama_url"], "http://192.168.1.50:11434")

    def test_ollama_url_must_stay_on_the_home_network(self):
        good = {"localhost": "http://localhost:11434", "http://10.0.0.4:8080": "http://10.0.0.4:8080",
                "https://gpu-box.local:11434/": "https://gpu-box.local:11434", "[fd00::5]:11434": "http://[fd00::5]:11434",
                "nas": "http://nas:11434", "": ""}
        for raw, want in good.items():
            self.assertEqual(system_api.safe_ollama_url(raw), want, raw)
        for bad in ("http://evil.example:11434", "http://8.8.8.8:11434", "http://user:pw@10.0.0.4:11434", "ftp://10.0.0.4:21",
                    "http://10.0.0.4:11434/api?x=1", "http://10.0.0.4:11434#f", "http://10.0.0.4:99999", "http://0.0.0.0:11434",
                    "http://10.0.0.4:11434\nNUXIVA_X=1", "http://[::ffff:8.8.8.8]:11434", "http://224.0.0.1:11434"):
            with self.assertRaises(HTTPException, msg=bad):
                system_api.safe_ollama_url(bad)
        with mock.patch.object(system_api, "env_get", lambda key, default="": "on"):
            self.assertEqual(system_api.safe_ollama_url("https://ollama.example.com:443"), "https://ollama.example.com:443")

    def test_model_names_cannot_inject_env_lines(self):
        self.assertEqual(system_api.safe_model(" qwen3:8b "), "qwen3:8b")
        self.assertEqual(system_api.safe_model("hf.co/org/model-GGUF:Q4_K_M"), "hf.co/org/model-GGUF:Q4_K_M")
        for bad in ("qwen\nNUXIVA_ADMIN=1", "a b", "$(rm -rf /)", "x" * 200):
            with self.assertRaises(HTTPException, msg=bad):
                system_api.safe_model(bad)


if __name__ == "__main__":
    unittest.main()
