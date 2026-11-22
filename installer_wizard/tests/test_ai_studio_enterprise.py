import tempfile
import unittest
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
from access import require_admin
from agenti.ai_studio import api
from agenti.ai_studio.audit_service import AuditService
from agenti.ai_studio.memory_service import CrossMemoryService
from agenti.ai_studio.preset_service import render_template
from agenti.ai_studio.service import StudioService
from agenti.ai_studio.smb_service import SmbStudioService
from agenti.ai_studio.store import StudioStore


class TemplateTests(unittest.TestCase):
    def test_render_template_replaces_known_and_keeps_unknown(self):
        self.assertEqual(render_template("Ciao {{ nome }} {{x}}", {"nome": "Ada"}), "Ciao Ada {{x}}")


class EnterpriseApiTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.store = StudioStore(db_path=root / "e.db")
        self.service = StudioService(
            store=self.store,
            smb=SmbStudioService(root_path=root / "smb"),
            memory=CrossMemoryService(store=self.store),
        )
        app = FastAPI()
        app.include_router(api.public_routes)
        app.include_router(api.admin_routes)
        app.dependency_overrides[require_admin] = lambda: "admin"
        api.service = self.service
        self.client = TestClient(app)

    def test_preset_crud_and_validation(self):
        res = self.client.post("/api/ai_studio/presets", json={"name": "Revisore", "system_prompt": "Sei un revisore.", "model_mode": "code"})
        self.assertEqual(res.status_code, 200)
        pid = res.json()["id"]
        self.assertEqual([p["id"] for p in self.client.get("/api/ai_studio/presets").json()], [pid])
        bad = self.client.post("/api/ai_studio/presets", json={"name": "x", "model_mode": "nope"})
        self.assertEqual(bad.status_code, 422)
        self.assertEqual(self.client.delete(f"/api/ai_studio/presets/{pid}").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/ai_studio/presets/{pid}").status_code, 404)

    def test_project_scoped_presets_are_filtered(self):
        proj = self.client.post("/api/ai_studio/projects", json={"name": "P", "description": "", "instructions": "", "smb_folder": ""}).json()["id"]
        self.client.post("/api/ai_studio/presets", json={"name": "Globale", "system_prompt": "g"})
        self.client.post("/api/ai_studio/presets", json={"name": "Locale", "system_prompt": "l", "project_id": proj})
        self.assertEqual(len(self.client.get("/api/ai_studio/presets").json()), 1)
        self.assertEqual(len(self.client.get("/api/ai_studio/presets", params={"project_id": proj}).json()), 2)

    def test_preset_is_injected_into_system_prompt(self):
        pid = self.service.presets.create("Pirata", "Rispondi come un pirata.")["id"]
        seen = {}

        async def fake(prompt, system, mode):
            seen["system"] = system
            return "ok"

        self.service._execute_inference = fake
        thread = self.service.create_thread(title="t", model_mode="fast")
        import asyncio
        asyncio.run(self.service.send_message(thread.id, "ciao", preset_id=pid))
        self.assertIn("Rispondi come un pirata.", seen["system"])

    def test_audit_records_actions_and_chain_verifies(self):
        self.client.post("/api/ai_studio/presets", json={"name": "A", "system_prompt": ""})
        entries = self.client.get("/api/ai_studio/audit").json()
        self.assertEqual(entries[0]["action"], "preset.create")
        self.assertTrue(self.client.get("/api/ai_studio/audit/verify").json()["ok"])

    def test_audit_detects_tampering(self):
        audit = AuditService(self.store)
        audit.append("u", "a.one", "x")
        audit.append("u", "a.two", "y")
        with self.store._lock, self.store._get_connection() as conn:
            conn.execute("UPDATE audit_log SET detail = 'forged' WHERE id = 1")
        result = audit.verify()
        self.assertFalse(result["ok"])
        self.assertEqual(result["broken_at"], 1)

    def test_sandbox_code_execution_python_success(self):
        res = self.client.post("/api/ai_studio/sandbox/run", json={"code": "print('hello_sandbox')", "language": "python"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["ok"])
        self.assertIn("hello_sandbox", data["output"])
        self.assertEqual(data["exit_code"], 0)

    def test_sandbox_code_execution_records_audit(self):
        self.client.post("/api/ai_studio/sandbox/run", json={"code": "1+1", "language": "python"})
        audit = self.client.get("/api/ai_studio/audit").json()
        self.assertEqual(audit[0]["action"], "code.execute")

    def test_stream_message_endpoint_sse(self):
        th = self.client.post("/api/ai_studio/threads", json={"title": "stream_test"}).json()
        res = self.client.post(f"/api/ai_studio/threads/{th['id']}/stream", json={"content": "ping"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/event-stream", res.headers.get("content-type", ""))
        self.assertIn("data:", res.text)
        self.assertIn("done", res.text)
