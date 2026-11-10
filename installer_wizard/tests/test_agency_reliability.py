import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from features.agency import client as client_module
from features.agency import runner, tools, workspace
from features.agency.memory import ProjectMemory


class FakeReliabilityAgency:
    def __init__(self) -> None:
        self.revoked_workers: set[str] = set()
        self.checkpoints: dict[str, str] = {}
        self.projects = {
            "p1": {
                "project": {"id": "p1", "title": "Store", "status": "running"},
                "tasks": [
                    {
                        "id": "t1",
                        "title": "Architettura",
                        "status": "review",
                        "feedback": None,
                        "checkpoint": "checkpoint deliverable v1",
                    }
                ],
                "folder": "store",
            }
        }

    async def call(self, op: str, **fields):
        if op == "code_files":
            worker = fields.get("worker")
            if worker in self.revoked_workers:
                raise client_module.AgencyRejected("revoked", "worker assignment revoked")
            return {"files": [{"path": "main.py", "bytes": 100, "language": "python"}]}
        if op == "task_update":
            worker = fields.get("worker")
            if worker in self.revoked_workers:
                raise client_module.AgencyRejected("revoked", "worker assignment revoked")
            task_id = fields["task"]
            action = fields["action"]
            if action == "submit":
                self.checkpoints[task_id] = fields.get("checkpoint", "")
                self.projects["p1"]["tasks"][0]["status"] = "review"
            elif action == "approve":
                self.projects["p1"]["tasks"][0]["status"] = "done"
            return self.projects["p1"]
        if op == "project_get":
            return self.projects[fields["id"]]
        if op == "assignment_revoke":
            self.revoked_workers.add(fields.get("worker", "agent-t1-g1"))
            return {"ok": True}
        raise NotImplementedError(op)


class ReliabilityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.fake = FakeReliabilityAgency()
        patches = [
            mock.patch.object(runner, "client", self.fake),
            mock.patch.object(tools, "client", self.fake),
            mock.patch.object(runner, "memory", ProjectMemory(self.tmp / "state")),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        (self.tmp / "store").mkdir(parents=True)

    def test_restart_during_review_preserves_checkpoint(self):
        data = asyncio.run(self.fake.call("project_get", id="p1"))
        task = data["tasks"][0]
        self.assertEqual(task["status"], "review")
        self.assertEqual(task["checkpoint"], "checkpoint deliverable v1")
        resumed = asyncio.run(
            self.fake.call("task_update", project="p1", task="t1", action="approve")
        )
        self.assertEqual(resumed["tasks"][0]["status"], "done")

    def test_revoked_agent_loses_tool_access_and_update_is_rejected(self):
        ctx = tools.Context(
            project_id="p1",
            folder=str(self.tmp / "store"),
            task="t1",
            worker="agent-t1-g1",
            generation=1,
        )
        files = asyncio.run(tools._list_files(ctx, {}))
        self.assertIn("main.py", files)

        asyncio.run(
            self.fake.call("assignment_revoke", project="p1", task="t1", worker="agent-t1-g1")
        )

        with self.assertRaises(client_module.AgencyRejected) as exc:
            asyncio.run(tools._list_files(ctx, {}))
        self.assertEqual(exc.exception.code, "revoked")

        with self.assertRaises(client_module.AgencyRejected) as exc:
            asyncio.run(
                self.fake.call(
                    "task_update",
                    project="p1",
                    task="t1",
                    action="submit",
                    worker="agent-t1-g1",
                    generation=1,
                )
            )
        self.assertEqual(exc.exception.code, "revoked")
