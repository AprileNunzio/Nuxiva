import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

import nuxiva_supervisor
from features.agency import blueprint as bp
from features.agency import client as client_module
from features.agency import critic, runner, service, workspace
from features.agency.memory import ProjectMemory
from features.shares import archive

HEADERS = {"X-Nuxiva-Request": "1"}

PLAN = {
    "title": "Negozio di informatica",
    "summary": "E-commerce con catalogo e carrello",
    "architecture": "FastAPI + PostgreSQL + React",
    "roles": [{"id": "Backend", "mission": "API"}, {"id": "frontend", "mission": "UI"}, {"id": "backend"}],
    "tasks": [
        {"id": "design", "title": "Architettura", "role": "backend", "acceptance": ["schema dati"], "estimate_seconds": 5},
        {"id": "api", "title": "API catalogo", "role": "backend", "depends_on": ["design", "ui"]},
        {"id": "ui", "title": "Vetrina", "role": "designer", "depends_on": ["design"]},
        {"id": "api", "title": "Duplicato", "role": "frontend"},
        {"title": ""},
    ],
}

CRITIQUE = {
    "questions": [{"q": "I pagamenti sono sicuri?", "a": "Serve un fornitore PCI"}],
    "issues": ["manca il checkout"],
    "missing_tasks": [{"id": "checkout", "title": "Checkout sicuro", "role": "backend", "depends_on": ["api"]}],
    "verdict": "ok",
}


class FakeAgency:
    def __init__(self) -> None:
        self.projects: dict[str, dict] = {}
        self.calls: list[tuple[str, dict]] = []

    async def call(self, op: str, **fields):
        self.calls.append((op, fields))
        return getattr(self, op)(**fields)

    def project_create(self, id, title, goal, workspace, budget):
        self.projects[id] = {"project": {"id": id, "title": title, "status": "planning"}, "tasks": []}
        return self.projects[id]

    def project_plan(self, id, tasks):
        state = self.projects[id]
        for spec in tasks:
            state["tasks"].append({**spec, "status": "pending", "feedback": None,
                                   "acceptance": [{"text": a, "verified": False} for a in spec["acceptance"]]})
        state["project"]["status"] = "running"
        return state

    def project_get(self, id):
        return self.projects[id]

    def project_list(self):
        return [{"project": p["project"], "progress": {"running": sum(t["status"] == "running" for t in p["tasks"])}}
                for p in self.projects.values()]

    def dispatch(self):
        started = []
        for project_id, state in self.projects.items():
            done = {t["id"] for t in state["tasks"] if t["status"] == "done"}
            for task in state["tasks"]:
                if task["status"] == "pending" and set(task["depends_on"]) <= done:
                    task["status"] = "running"
                    started.append({"project": project_id, "task": task["id"]})
        return {"started": started, "capacity": 4}

    def task_update(self, project, task, action, feedback=None, tokens=0, seconds=0):
        target = next(t for t in self.projects[project]["tasks"] if t["id"] == task)
        target["status"] = {"submit": "review", "approve": "done", "rework": "pending",
                            "fail": "failed", "interrupt": "pending"}[action]
        target["feedback"] = feedback
        return self.projects[project]


def scripted(*replies):
    queue = list(replies)

    async def generate(prompt, **kwargs):
        if not queue:
            raise service.BrainUnavailable("script finished")
        item = queue.pop(0)
        return item(prompt, kwargs) if callable(item) else item
    return generate


class AgencyCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.fake = FakeAgency()
        patches = [
            mock.patch.object(archive, "ROOT", self.tmp / "condivisa"),
            mock.patch.object(service, "client", self.fake),
            mock.patch.object(runner, "client", self.fake),
            mock.patch.object(service, "memory", ProjectMemory(self.tmp / "state")),
            mock.patch.object(runner, "memory", ProjectMemory(self.tmp / "state")),
            mock.patch.object(service.store, "event"),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        (self.tmp / "condivisa" / "09 Progetti").mkdir(parents=True)

    def start_project(self):
        with mock.patch("features.brain.llm.generate", scripted(PLAN, CRITIQUE)):
            return asyncio.run(service.start("Creami un e-commerce di informatica", "it"))


class BlueprintTest(unittest.TestCase):
    def test_parse_sanitises_roles_tasks_and_dependencies(self):
        plan = bp.parse(PLAN, "goal")
        self.assertEqual([r.id for r in plan.roles], ["backend", "frontend"])
        ids = [t.id for t in plan.tasks]
        self.assertEqual(ids[:3], ["design", "api", "ui"])
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(plan.tasks[1].depends_on, ["design"])
        self.assertEqual(plan.tasks[2].role, "backend")
        self.assertEqual(plan.tasks[0].estimate_seconds, 60)
        self.assertEqual(plan.tasks[0].spec()["max_attempts"], 3)

    def test_garbage_gives_an_empty_but_valid_plan(self):
        plan = bp.parse("not json", "obiettivo")
        self.assertEqual(plan.title, "obiettivo")
        self.assertEqual(plan.tasks, [])
        self.assertEqual(plan.roles[0].id, "generalist")

    def test_task_limit(self):
        plan = bp.parse({"tasks": [{"title": f"t{i}"} for i in range(200)]}, "g")
        self.assertEqual(len(plan.tasks), bp.MAX_TASKS)
        self.assertEqual(bp.extend(plan, [{"title": "more"}]), [])


class CriticTest(unittest.TestCase):
    def test_interrogate_records_questions_and_adds_missing_tasks(self):
        plan = bp.parse(PLAN, "goal")
        with mock.patch("features.brain.llm.generate", scripted(CRITIQUE)):
            reasoning, tokens = asyncio.run(critic.interrogate("goal", plan, "italiano"))
        self.assertEqual(reasoning.added, ["checkout"])
        self.assertEqual(reasoning.exchanges[0].question, "I pagamenti sono sicuri?")
        self.assertEqual(plan.tasks[-1].depends_on, ["api"])
        self.assertGreater(tokens, 0)

    def test_review_never_approves_without_explicit_verdict(self):
        task = {"title": "x", "acceptance": ["y"]}
        with mock.patch("features.brain.llm.generate", scripted({}, {"verdict": "approve"}, {"verdict": "approve"})):
            self.assertFalse(asyncio.run(critic.review(task, "lavoro", "italiano")).approved)
            self.assertTrue(asyncio.run(critic.review(task, "lavoro", "italiano")).approved)
            self.assertFalse(asyncio.run(critic.review(task, "  ", "italiano")).approved)


class WorkspaceTest(AgencyCase):
    def test_rejects_escape_and_hidden_files(self):
        for folder, name in (("../fuori", "a.md"), ("ok", "../a.md"), ("ok", ".ssh/x"), ("ok", "")):
            with self.assertRaises(workspace.WorkspaceError):
                workspace.write(folder, name, "x")
        path = workspace.write("ok", "Lavori/a.md", "ciao")
        self.assertEqual(path.read_text(), "ciao")
        self.assertEqual(workspace.read("ok", "Lavori/a.md"), "ciao")

    def test_refuses_symlinked_files(self):
        target = self.tmp / "secret.txt"
        target.write_text("segreto")
        folder = workspace.folder("ok")
        folder.mkdir()
        (folder / "link.md").symlink_to(target)
        self.assertEqual(workspace.read("ok", "link.md"), "")
        with self.assertRaises(OSError):
            workspace.write("ok", "link.md", "x")


class ServiceTest(AgencyCase):
    def test_start_plans_writes_documents_and_registers_tasks(self):
        detail = self.start_project()
        self.assertEqual(detail["project"]["status"], "running")
        ops = [op for op, _ in self.fake.calls]
        self.assertEqual(ops, ["project_create", "project_plan"])
        tasks = self.fake.calls[1][1]["tasks"]
        self.assertIn("checkout", [t["id"] for t in tasks])
        folders = list((self.tmp / "condivisa" / "09 Progetti").iterdir())
        self.assertEqual(len(folders), 1)
        self.assertIn("Negozio di informatica", (folders[0] / "PIANO.md").read_text())
        self.assertIn("I pagamenti sono sicuri?", (folders[0] / "RAGIONAMENTO.md").read_text())

    def test_short_goal_and_empty_plan_are_refused(self):
        with self.assertRaises(service.AgencyFailure) as short:
            asyncio.run(service.start("ciao", "it"))
        self.assertEqual(short.exception.code, "goal")
        with mock.patch("features.brain.llm.generate", scripted({"tasks": []})):
            with self.assertRaises(service.AgencyFailure) as empty:
                asyncio.run(service.start("Creami un sito per la pizzeria", "it"))
        self.assertEqual(empty.exception.code, "empty_plan")
        self.assertEqual(self.fake.calls, [])


class RunnerTest(AgencyCase):
    def drive(self, replies, rounds=6):
        engine = runner.Runner()

        async def go():
            with mock.patch("features.brain.llm.generate", scripted(*replies)):
                for _ in range(rounds):
                    await engine.tick()
                    while engine.inflight:
                        await asyncio.gather(*list(engine.inflight.values()), return_exceptions=True)
        asyncio.run(go())

    def test_tasks_run_in_dependency_order_and_are_reviewed(self):
        self.start_project()
        project = next(iter(self.fake.projects.values()))
        order = []

        def work(prompt, kwargs):
            order.append(prompt.split("Task: ")[1].split("\n")[0])
            return "## Consegna\nlavoro completo"
        approve = {"verdict": "approve"}
        self.drive([work, approve] * 5)
        self.assertEqual([t["status"] for t in project["tasks"]], ["done"] * 5)
        self.assertEqual(order[0], "Architettura")
        self.assertEqual(order[-1], "Checkout sicuro")
        folder = next((self.tmp / "condivisa" / "09 Progetti").iterdir())
        self.assertTrue((folder / "Lavori" / "checkout.md").is_file())

    def test_rework_uses_fallback_feedback_when_review_is_unclear(self):
        self.start_project()
        project = next(iter(self.fake.projects.values()))
        self.drive(["bozza", {}], rounds=1)
        design = project["tasks"][0]
        self.assertEqual(design["status"], "pending")
        self.assertIn("criteri", design["feedback"])

    def test_missing_brain_interrupts_instead_of_failing(self):
        self.start_project()
        project = next(iter(self.fake.projects.values()))

        def down(prompt, kwargs):
            raise service.BrainUnavailable("offline")
        self.drive([down], rounds=1)
        self.assertEqual(project["tasks"][0]["status"], "pending")

    def test_reconcile_interrupts_orphaned_running_tasks(self):
        self.start_project()
        project = next(iter(self.fake.projects.values()))
        project["tasks"][0]["status"] = "running"
        asyncio.run(runner.Runner().reconcile())
        self.assertEqual(project["tasks"][0]["status"], "pending")


class ClientTest(unittest.TestCase):
    def test_unreachable_socket_raises_unavailable(self):
        missing = client_module.AgencyClient(Path(tempfile.mkdtemp()) / "none.sock", timeout=1)
        with self.assertRaises(client_module.AgencyUnavailable):
            asyncio.run(missing.call("ping"))

    def test_rejections_carry_the_daemon_code(self):
        path = Path(tempfile.mkdtemp()) / "a.sock"

        async def handle(reader, writer):
            request = json.loads(await reader.readline())
            reply = {"ok": True, "data": {"pong": True}} if request["op"] == "ping" else \
                {"ok": False, "error": {"code": "not_found", "message": "project not found"}}
            writer.write(json.dumps(reply).encode() + b"\n")
            await writer.drain()
            writer.close()

        async def go():
            server = await asyncio.start_unix_server(handle, path=str(path))
            agency = client_module.AgencyClient(path, timeout=2)
            async with server:
                self.assertEqual(await agency.call("ping"), {"pong": True})
                with self.assertRaises(client_module.AgencyRejected) as rejected:
                    await agency.call("project_get", id="x")
                self.assertEqual(rejected.exception.code, "not_found")
        asyncio.run(go())


class ApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = TestClient(nuxiva_supervisor.admin)
        assert cls.admin.post("/api/auth/login", json={"username": "admin", "password": "nuxiva"}, headers=HEADERS).status_code == 200

    def test_short_goal_is_rejected_with_a_translated_key(self):
        r = self.admin.post("/api/agency/projects", json={"goal": "ciao"}, headers=HEADERS)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["detail"]["code"], "goal")

    def test_engine_offline_answers_503(self):
        offline = client_module.AgencyClient(Path(tempfile.mkdtemp()) / "none.sock", timeout=1)
        with mock.patch.object(service, "client", offline):
            r = self.admin.get("/api/agency", headers=HEADERS)
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["detail"]["code"], "unavailable")

    def test_bad_ids_and_actions(self):
        self.assertEqual(self.admin.post("/api/agency/projects/Bad..id/pause", headers=HEADERS).status_code, 404)
        self.assertEqual(self.admin.post("/api/agency/projects/ok/explode", headers=HEADERS).status_code, 400)
