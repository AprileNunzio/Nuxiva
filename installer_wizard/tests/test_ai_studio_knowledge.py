import tempfile
import unittest
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
from access import require_admin
from agenti.ai_studio import api
from agenti.ai_studio.knowledge_service import build_match_query, chunk_text
from agenti.ai_studio.memory_service import CrossMemoryService
from agenti.ai_studio.service import StudioService
from agenti.ai_studio.smb_service import SmbStudioService
from agenti.ai_studio.store import StudioStore


class ChunkingTests(unittest.TestCase):
    def test_chunk_text_respects_size_and_splits_long_paragraphs(self):
        chunks = chunk_text("a" * 2000, size=900, overlap=100)
        self.assertGreater(len(chunks), 2)
        self.assertTrue(all(len(c) <= 900 for c in chunks))

    def test_chunk_text_empty(self):
        self.assertEqual(chunk_text("   "), [])

    def test_match_query_sanitizes_operators(self):
        q = build_match_query('rete" OR NEAR(x) -- DROP')
        self.assertNotIn("--", q)
        self.assertNotIn("(", q)
        self.assertEqual(build_match_query("!!"), "")


class KnowledgeApiTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        store = StudioStore(db_path=root / "k.db")
        self.service = StudioService(
            store=store,
            smb=SmbStudioService(root_path=root / "smb"),
            memory=CrossMemoryService(store=store),
        )
        app = FastAPI()
        app.include_router(api.public_routes)
        app.include_router(api.admin_routes)
        app.dependency_overrides[require_admin] = lambda: "admin"
        api.service = self.service
        self.client = TestClient(app)
        self.pid = self.client.post(
            "/api/ai_studio/projects",
            json={"name": "Alpha", "description": "", "instructions": "", "smb_folder": ""},
        ).json()["id"]

    def test_add_search_and_delete_document(self):
        base = f"/api/ai_studio/projects/{self.pid}/knowledge"
        doc = self.client.post(base, json={"name": "guida.md", "content": "Il router usa la porta 8080.\n\nLa pompa lavora a 12 volt."}).json()
        self.assertEqual(doc["name"], "guida.md")
        hits = self.client.get(f"{base}/search", params={"q": "porta router"}).json()
        self.assertEqual(hits[0]["source"], "guida.md")
        self.assertIn("8080", hits[0]["snippet"])
        self.assertEqual(len(self.client.get(base).json()), 1)
        self.assertEqual(self.client.delete(f"{base}/{doc['id']}").status_code, 200)
        self.assertEqual(self.client.get(f"{base}/search", params={"q": "router"}).json(), [])

    def test_unknown_project_is_404(self):
        self.assertEqual(self.client.get("/api/ai_studio/projects/nope/knowledge").status_code, 404)

    def test_context_contains_source(self):
        self.service.knowledge.add_document(self.pid, "note.txt", "La stampante 3D usa PLA a 200 gradi.")
        ctx = self.service.knowledge.build_context(self.pid, "temperatura PLA stampante")
        self.assertIn("[note.txt]", ctx)

    def test_projects_are_isolated(self):
        self.service.knowledge.add_document(self.pid, "a.txt", "segreto alfa")
        self.assertEqual(self.service.knowledge.search("altro_progetto", "segreto"), [])
