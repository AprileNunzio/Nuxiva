import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

import nuxiva_supervisor
from features.agency import api, board, service
from features.agency.client import AgencyUnavailable
from features.agency.forge import registry as forge_registry
from features.agency.forge.registry import ForgedTool
from features.agency.memory import ProjectMemory

HEADERS = {"X-Nuxiva-Request": "1"}


def summary(pid, title, created, status="running", percent=40):
    project = {"id": pid, "title": title, "goal": "obiettivo segreto " * 40, "status": status, "workspace": "x",
               "budget": {"tokens": 1000, "seconds": 60, "parallel": 2}, "usage": {"tokens": 120, "seconds": 90},
               "created_at_ms": created}
    progress = {"total": 3, "pending": 1, "running": 1, "review": 0, "done": 1, "failed": 0, "cancelled": 0,
                "blocked": 0, "percent": percent}
    return {"project": project, "progress": progress, "critical_path_seconds": 600}


class Engine:
    def __init__(self, down=False):
        self.down = down
        self.calls = []

    async def call(self, op, **fields):
        self.calls.append((op, fields))
        if self.down:
            raise AgencyUnavailable("offline")
        if op == "capacity":
            return {"running": 2, "capacity": {"parallel_agents": 4, "limit": "auto"}, "host": {}}
        if op == "project_list":
            return [summary("vecchio", "Vecchio", 1), summary("shop", "Negozio‮", 5, percent=250)]
        if op == "project_get":
            return {**summary(fields["id"], "Negozio", 5), "tasks": [
                {"id": "design", "title": "Architettura", "role": "backend", "status": "done", "attempts": 1,
                 "depends_on": [], "feedback": "nascosto", "acceptance": [{"text": "x", "verified": True}]},
                {"id": "api", "title": "API", "role": "backend", "status": "running", "attempts": 0, "depends_on": ["design"]},
            ]}
        if op == "project_control":
            return {"ok": True}
        raise AssertionError(op)


class BoardCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.engine = Engine()
        memory = ProjectMemory(self.tmp / "state")
        memory.save("shop", {"blueprint": {"summary": "E-commerce", "roles": [{"id": "backend", "mission": "API"}]},
                             "reasoning": {"exchanges": [{"question": "Pagamenti?", "answer": "PCI"}], "issues": ["checkout"]}})
        for patcher in (mock.patch.object(service, "client", self.engine), mock.patch.object(service, "memory", memory),
                        mock.patch.object(forge_registry.registry, "directory", self.tmp / "state")):
            patcher.start()
            self.addCleanup(patcher.stop)
        forge_registry.registry.add(ForgedTool(name="iva_netta", description="d", args={}, origin={"project": "shop"},
                                               code="def run(args):\n    return 1\n", tests=[]))


class BoardTest(BoardCase):
    def test_overview_is_sanitised_and_newest_first(self):
        data = asyncio.run(board.overview())
        self.assertEqual(data["agents"], {"running": 2, "parallel": 4})
        self.assertEqual(data["tools"], 1)
        self.assertEqual([p["id"] for p in data["projects"]], ["shop", "vecchio"])
        shop = data["projects"][0]
        self.assertEqual((shop["title"], shop["percent"], shop["eta_seconds"]), ("Negozio", 100, 600))
        self.assertNotIn("goal", shop)

    def test_focus_exposes_only_display_fields(self):
        data = asyncio.run(board.focus("shop"))
        self.assertEqual([t["id"] for t in data["tasks"]], ["design", "api"])
        self.assertEqual(data["tasks"][1]["depends_on"], ["design"])
        self.assertNotIn("feedback", data["tasks"][0])
        self.assertNotIn("acceptance", data["tasks"][0])
        self.assertEqual(data["questions"], [{"q": "Pagamenti?", "a": "PCI"}])
        self.assertEqual(data["tools"], ["x_iva_netta"])
        self.assertLessEqual(len(data["goal"]), 400)

    def test_card_tolerates_garbage(self):
        card = board.card({"project": {"usage": {"tokens": -5}}, "progress": {"percent": True}})
        self.assertEqual((card["tokens"], card["percent"], card["id"]), (0, 0, ""))


class BoardApiTest(BoardCase):
    @classmethod
    def setUpClass(cls):
        cls.web = TestClient(nuxiva_supervisor.public)

    def allow(self):
        patcher = mock.patch.object(api, "require_display", lambda request: None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_strangers_are_refused(self):
        self.assertEqual(self.web.get("/api/agency/board").status_code, 401)
        self.assertEqual(self.web.post("/api/agency/board/shop/pause", headers=HEADERS).status_code, 401)

    def test_display_reads_and_controls(self):
        self.allow()
        self.assertEqual(self.web.get("/api/agency/board").json()["projects"][0]["id"], "shop")
        self.assertEqual(self.web.get("/api/agency/board/shop").json()["roles"], [{"id": "backend", "mission": "API"}])
        self.assertEqual(self.web.post("/api/agency/board/shop/pause", headers=HEADERS).status_code, 200)
        self.assertIn(("project_control", {"id": "shop", "action": "pause"}), self.engine.calls)
        self.assertEqual(self.web.post("/api/agency/board/shop/cancel", headers=HEADERS).status_code, 400)
        self.assertEqual(self.web.post("/api/agency/board/shop/pause").status_code, 403)
        self.assertEqual(self.web.get("/api/agency/board/Bad..Id").status_code, 404)

    def test_voice_creation_is_queued(self):
        self.allow()
        with mock.patch.object(api, "background") as queued, mock.patch.object(service, "launch", mock.MagicMock()) as launch:
            r = self.web.post("/api/agency/board/projects", json={"goal": "Creami un e-commerce di informatica"}, headers=HEADERS)
        self.assertEqual(r.status_code, 202)
        queued.assert_called_once()
        launch.assert_called_once()
        self.assertEqual(self.web.post("/api/agency/board/projects", json={"goal": "ciao"}, headers=HEADERS).status_code, 400)

    def test_offline_engine_answers_503(self):
        self.allow()
        self.engine.down = True
        r = self.web.get("/api/agency/board")
        self.assertEqual((r.status_code, r.json()["detail"]["code"]), (503, "unavailable"))


if __name__ == "__main__":
    unittest.main()
