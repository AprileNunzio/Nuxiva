import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from access import require_admin
from agenti.ai_studio import api
from agenti.ai_studio.memory_service import CrossMemoryService
from agenti.ai_studio.service import StudioService
from agenti.ai_studio.smb_service import SmbStudioService
from agenti.ai_studio.store import StudioStore


class ReactionRoutesTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        store = StudioStore(db_path=root / "r.db")
        self.service = StudioService(store=store, smb=SmbStudioService(root_path=root / "smb"),
                                     memory=CrossMemoryService(store=store))

        async def fake(prompt, system, mode):
            return "risposta"

        self.service._execute_inference = fake
        api.service = self.service
        app = FastAPI()
        app.include_router(api.admin_routes)
        app.dependency_overrides[require_admin] = lambda: "nunzio"
        self.client = TestClient(app)
        self.thread = self.client.post("/api/ai_studio/threads", json={"title": "t"}).json()["id"]
        self.message = self.client.post(f"/api/ai_studio/threads/{self.thread}/messages", json={"content": "ciao"}).json()["id"]

    def path(self, suffix: str, thread: str = "") -> str:
        return f"/api/ai_studio/threads/{thread or self.thread}/messages/{self.message}/{suffix}"

    def listed(self) -> dict:
        items = self.client.get(f"/api/ai_studio/threads/{self.thread}/messages").json()
        return next(m for m in items if m["id"] == self.message)

    def test_reaction_toggles_and_persists(self):
        res = self.client.post(self.path("reactions"), json={"emoji": "🚀"})
        self.assertEqual(res.json()["reactions"], [{"emoji": "🚀", "count": 1, "authors": ["nunzio"]}])
        self.assertEqual(self.listed()["reactions"][0]["emoji"], "🚀")
        self.client.post(self.path("reactions"), json={"emoji": "🚀"})
        self.assertEqual(self.listed()["reactions"], [])

    def test_feedback_persists_and_clears(self):
        self.assertEqual(self.client.put(self.path("feedback"), json={"value": "negative"}).json()["feedback"], "negative")
        self.assertEqual(self.listed()["feedback"], "negative")
        self.client.put(self.path("feedback"), json={"value": None})
        self.assertIsNone(self.listed()["feedback"])

    def test_rejects_unknown_emoji_values_and_foreign_threads(self):
        self.assertEqual(self.client.post(self.path("reactions"), json={"emoji": "<script>"}).status_code, 400)
        self.assertEqual(self.client.put(self.path("feedback"), json={"value": "evil"}).status_code, 422)
        other = self.client.post("/api/ai_studio/threads", json={"title": "o"}).json()["id"]
        self.assertEqual(self.client.post(self.path("reactions", other), json={"emoji": "🚀"}).status_code, 404)

    def test_deleting_thread_drops_marks(self):
        self.client.post(self.path("reactions"), json={"emoji": "💡"})
        self.client.delete(f"/api/ai_studio/threads/{self.thread}")
        with self.service.store._get_connection() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM message_marks").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
