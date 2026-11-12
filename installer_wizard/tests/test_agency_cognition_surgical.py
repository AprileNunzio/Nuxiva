import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

import nuxiva_supervisor
from features.agency import agent, api, cognition, service, tools, workspace
from features.agency.memory import ProjectMemory

HEADERS = {"X-Nuxiva-Request": "1"}


class AgencyCognitionAndSurgicalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.web = TestClient(nuxiva_supervisor.public)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        patcher_ws = mock.patch.object(workspace, "root", return_value=self.root / "projects")
        patcher_ws.start()
        self.addCleanup(patcher_ws.stop)

    def test_cognition_evaluate_interrogate_and_recruit_for_ecommerce(self):
        verdict = cognition.evaluate_candidates([
            {
                "id": "monolith",
                "title": "Single Script Store",
                "completeness": 65,
                "modularity": 45,
                "security": 60,
                "feasibility": 90,
                "risk_penalty": 30,
            },
            {
                "id": "modular-agency",
                "title": "Modular Hardware E-Commerce",
                "completeness": 96,
                "modularity": 95,
                "security": 94,
                "feasibility": 90,
                "risk_penalty": 5,
            },
        ])
        self.assertEqual(verdict["selected_id"], "modular-agency")
        goal = "Creami un progetto di un sito e-commerce di informatica con catalogo GPU e carrello"
        report_open = cognition.interrogate_goal(goal, [])
        self.assertGreaterEqual(report_open["escalate_count"], 1)
        report_resolved = cognition.interrogate_goal(goal, ["pagamento checkout: Stripe sandbox"])
        self.assertEqual(report_resolved["escalate_count"], 0)
        self.assertTrue(report_resolved["ready_for_autonomous_execution"])
        roles = cognition.recruit_specialists(goal, "FastAPI + React + SQLite")
        role_ids = {r["id"] for r in roles}
        self.assertIn("architect", role_ids)
        self.assertIn("backend", role_ids)
        self.assertIn("frontend", role_ids)
        self.assertIn("commerce_specialist", role_ids)

    def test_surgical_outline_view_range_and_replace_content(self):
        folder = "Ecommerce Informatica abc123"
        sample_code = (
            "class HardwareCatalog:\n"
            "    def list_gpus(self):\n"
            "        return ['RTX-4080']\n\n"
            "def compute_total(price: int, qty: int) -> int:\n"
            "    return price * qty\n"
        )
        workspace.write(folder, "src/catalog.py", sample_code)
        ctx = tools.Context(project_id="proj-ec", folder=folder)

        outline_out = asyncio.run(tools.call(ctx, "view_outline", {"path": "src/catalog.py"}))
        self.assertIn("src/catalog.py", outline_out)

        range_out = asyncio.run(tools.call(ctx, "view_range", {
            "path": "src/catalog.py",
            "start_line": 5,
            "end_line": 6,
        }))
        self.assertIn("5: def compute_total(price: int, qty: int) -> int:", range_out)

        fake_patch = {
            "patch": {
                "path": "src/catalog.py",
                "applied_chunks": 1,
                "old_lines": 6,
                "new_lines": 6,
                "sha256_before": "a" * 64,
                "sha256_after": "b" * 64,
            }
        }
        with mock.patch("features.agency.surgical.ops.client.call", mock.AsyncMock(return_value=fake_patch)):
            patch_out = asyncio.run(tools.call(ctx, "replace_content", {
                "path": "src/catalog.py",
                "start_line": 2,
                "end_line": 3,
                "target_content": "        return ['RTX-4080']",
                "replacement_content": "        return ['RTX-4080', 'RTX-4090']",
            }))
        self.assertIn("patched src/catalog.py: applied 1 chunk(s)", patch_out)
        self.assertIn("src/catalog.py", ctx.written)

    def test_agent_executes_parallel_tool_batch(self):
        folder = "Batch Project 999999"
        workspace.write(folder, "a.py", "def alpha():\n    return 1\n")
        workspace.write(folder, "b.py", "def beta():\n    return 2\n")
        ctx = tools.Context(project_id="proj-batch", folder=folder)
        replies = [
            {
                "thought": "Read both files in parallel",
                "batch": [
                    {"tool": "read_file", "args": {"path": "a.py"}},
                    {"tool": "read_file", "args": {"path": "b.py"}},
                ],
            },
            {
                "thought": "Both files inspected",
                "final": "Verified alpha and beta modules.",
            },
        ]
        brief = {
            "goal": "Inspect modules",
            "architecture": "Modular Python",
            "mission": "Backend verification",
            "inputs": "",
            "language_name": "Italian",
        }
        task = {"id": "t-check", "title": "Verify modules", "role": "backend", "acceptance": ["Modules verified"]}
        with mock.patch("features.agency.agent.llm.generate", mock.AsyncMock(side_effect=replies)):
            outcome = asyncio.run(agent.act(brief, task, ctx))
        self.assertEqual(outcome.steps, 2)
        self.assertIn("Verified alpha and beta", outcome.summary)

    def test_cognition_api_endpoint(self):
        memory = ProjectMemory(self.root / "state")
        memory.save("proj1", {"blueprint": {"architecture": "FastAPI + React"}})
        fake_detail = {
            "project": {
                "id": "proj1",
                "title": "Store",
                "goal": "Creami un progetto di un sito e-commerce di informatica",
                "decisions": [{"topic": "pagamento checkout", "choice": "Stripe sandbox"}],
            },
            "blueprint": {"architecture": "FastAPI + React"},
            "tasks": [],
        }
        with mock.patch.object(service, "memory", memory), \
             mock.patch.object(api, "require_display", lambda request: None), \
             mock.patch.object(service, "detail", mock.AsyncMock(return_value=fake_detail)):
            res = self.web.get("/api/agency/board/proj1/cognition", headers=HEADERS)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["project_id"], "proj1")
        self.assertIn("socratic", body)
        self.assertIn("specialists", body)
        self.assertTrue(body["socratic"]["ready_for_autonomous_execution"])


if __name__ == "__main__":
    unittest.main()
