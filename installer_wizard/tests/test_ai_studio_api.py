import tempfile
import unittest
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
from access import require_admin
from agenti.ai_studio import api
from agenti.ai_studio.artifact_extractor import ArtifactExtractor
from agenti.ai_studio.memory_service import CrossMemoryService
from agenti.ai_studio.service import StudioService
from agenti.ai_studio.smb_service import SmbStudioService
from agenti.ai_studio.store import StudioStore


class AiStudioApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.db_path = self.root / "test_studio.db"
        self.smb_root = self.root / "smb"

        self.store = StudioStore(db_path=self.db_path)
        self.smb = SmbStudioService(root_path=self.smb_root)
        self.memory = CrossMemoryService(store=self.store)
        self.service = StudioService(store=self.store, smb=self.smb, memory=self.memory)

        self.app = FastAPI()
        self.app.include_router(api.admin_routes)
        self.app.dependency_overrides[require_admin] = lambda: "admin"
        api.service = self.service

        async def fake_inference(prompt, system, mode):
            return f"<thought>Analisi in modalità {mode}</thought>Risposta di prova a: {prompt[-60:]}"

        self.service._execute_inference = fake_inference
        self.client = TestClient(self.app)

    def test_project_and_thread_lifecycle(self):
        res_proj = self.client.post(
            "/api/ai_studio/projects",
            json={
                "name": "Progetto Alpha",
                "description": "Descrizione Alpha",
                "instructions": "Usa Rust e Clean Architecture",
                "smb_folder": "09 Progetti/alpha",
            },
        )
        self.assertEqual(res_proj.status_code, 200)
        proj_data = res_proj.json()
        self.assertEqual(proj_data["name"], "Progetto Alpha")
        project_id = proj_data["id"]

        res_th = self.client.post(
            "/api/ai_studio/threads",
            json={
                "title": "Discussione Alpha",
                "project_id": project_id,
                "model_mode": "reasoning",
            },
        )
        self.assertEqual(res_th.status_code, 200)
        th_data = res_th.json()
        thread_id = th_data["id"]
        self.assertEqual(th_data["project_id"], project_id)

        res_msg = self.client.post(
            f"/api/ai_studio/threads/{thread_id}/messages",
            json={
                "content": "Crea una funzione Rust per calcolare fibonacci",
                "attachments": [],
            },
        )
        self.assertEqual(res_msg.status_code, 200)
        msg_data = res_msg.json()
        self.assertEqual(msg_data["role"], "assistant")
        self.assertIn("thought", msg_data)

        res_list = self.client.get(f"/api/ai_studio/threads/{thread_id}/messages")
        self.assertEqual(res_list.status_code, 200)
        messages = res_list.json()
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[1]["role"], "assistant")

    def test_zero_trust_smb_path_traversal(self):
        res_illegal = self.client.get("/api/ai_studio/smb/tree?folder=../../etc")
        self.assertEqual(res_illegal.status_code, 400)

        with self.assertRaises(ValueError):
            self.smb.validate_relative_path("../secret.key")

        with self.assertRaises(ValueError):
            self.smb.validate_relative_path("folder\0malicious")

        with self.assertRaises(ValueError):
            self.smb.validate_relative_path("safe/../../../root")

        safe_path = self.smb.validate_relative_path("01 Documenti/report.txt")
        self.assertTrue(str(safe_path).startswith(str(self.smb_root.resolve())))

    def test_artifact_extraction(self):
        llm_output = (
            "Ecco la soluzione richiesta:\n\n"
            "```rust:main.rs\n"
            "fn main() {\n"
            "    println!(\"Hello Nuxiva\");\n"
            "}\n"
            "```\n\n"
            "E la pagina web:\n\n"
            "```html:index.html\n"
            "<!DOCTYPE html>\n"
            "<html><body><h1>Studio</h1></body></html>\n"
            "```\n"
        )
        artifacts = ArtifactExtractor.extract(llm_output)
        self.assertEqual(len(artifacts), 2)
        self.assertEqual(artifacts[0].title, "main.rs")
        self.assertEqual(artifacts[0].language, "rust")
        self.assertEqual(artifacts[0].kind, "code")
        self.assertEqual(artifacts[1].title, "index.html")
        self.assertEqual(artifacts[1].language, "html")
        self.assertEqual(artifacts[1].kind, "html")

    def test_cross_memory_indexing_and_recall(self):
        self.memory.learn(
            content="Il server Nuxiva usa porta 8080 per la console web",
            source="written_chat",
            speaker="admin",
            tags=["network", "port"],
        )
        self.memory.learn(
            content="L'utente preferisce il tema scuro e la lingua italiana",
            source="voice_speech",
            speaker="nunzio",
            tags=["voice", "preferences"],
        )

        recalls = self.memory.recall("porta console web", limit=2)
        self.assertTrue(len(recalls) >= 1)
        self.assertIn("8080", recalls[0].content)

        injection = self.memory.build_system_injection("preferenze tema lingua")
        self.assertIn("preferisce il tema scuro", injection)

    def test_caching_hit_and_trim(self):
        th = self.service.create_thread(title="Cache Test Thread", model_mode="fast")
        msg1 = self.client.post(
            f"/api/ai_studio/threads/{th.id}/messages",
            json={"content": "Definisci un mutex in Rust", "attachments": []},
        )
        self.assertEqual(msg1.status_code, 200)
        data1 = msg1.json()
        self.assertFalse(data1.get("cached", False))

        other = self.service.create_thread(title="Cache Test Thread 2", model_mode="fast")
        msg2 = self.client.post(
            f"/api/ai_studio/threads/{other.id}/messages",
            json={"content": "Definisci un mutex in Rust", "attachments": []},
        )
        self.assertEqual(msg2.status_code, 200)
        data2 = msg2.json()
        self.assertEqual(data1["content"], data2["content"])

    def test_memory_consolidation_endpoint(self):
        self.memory.learn("Preferisco il linguaggio Rust", "written_chat", "user")
        self.memory.learn("Preferisco il linguaggio Rust", "voice_speech", "user")
        res = self.client.post("/api/ai_studio/memory/consolidate")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("consolidated", data)
        self.assertIn("pruned", data)

