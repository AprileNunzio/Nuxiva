import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from server.features.repair_workbench.session_models import WorkbenchSession
from server.features.repair_workbench.team_models import (
    CreateIssueRequest, RunTeamRequest, UpdateIssueRequest, WorkerResult,
)
from server.features.repair_workbench.team_service import WORKERS, WorkbenchTeamService


class Store:
    def __init__(self):
        self.session = WorkbenchSession(session_id="session", project_id="project", owner_id="owner",
                                        created_at=1, updated_at=1)
        self.saved = None

    def get(self, owner, session_id):
        if owner != "owner" or session_id != "session":
            raise PermissionError()
        return self.session

    def remember(self, session):
        self.saved = session.model_dump_json()


class WorkbenchTeamTests(unittest.IsolatedAsyncioTestCase):
    async def _settle(self, service):
        for _ in range(30):
            await asyncio.sleep(0)
            tasks = [task for task in service._automatic.values() if not task.done()]
            if not tasks:
                return
        await asyncio.wait_for(asyncio.gather(*tasks), 2)

    async def test_first_observation_runs_and_motion_does_not_duplicate_work(self):
        store = Store()
        execute = AsyncMock(return_value=WorkerResult(summary="reviewed"))
        service = WorkbenchTeamService(store, None, {"diagnosis": execute}, automatic_interval=0)
        await service.observe("owner", "session")
        self.assertFalse(service._automatic)
        store.session.dossier.title = "Controller PCB42"
        await service.observe("owner", "session")
        await self._settle(service)
        self.assertEqual(execute.await_count, 1)
        store.session.dossier.summary = "The same board at a new angle"
        await service.observe("owner", "session")
        await self._settle(service)
        self.assertEqual(execute.await_count, 1)
        self.assertEqual(len(store.session.team.tasks), 5)

    async def test_new_issue_is_coalesced_during_running_team_and_can_be_resolved(self):
        store = Store()
        started, release = asyncio.Event(), asyncio.Event()
        messages = []

        async def execute(_session, message):
            messages.append(message)
            started.set()
            await release.wait()
            return WorkerResult(summary="reviewed")

        service = WorkbenchTeamService(store, None, {"diagnosis": execute}, automatic_interval=0)
        service.issue("owner", "session", CreateIssueRequest(title="No audio"))
        await asyncio.wait_for(started.wait(), 2)
        service.issue("owner", "session", CreateIssueRequest(title="Hot component"))
        service.issue("owner", "session", CreateIssueRequest(title="Hot component"))
        release.set()
        await self._settle(service)
        self.assertEqual(len(messages), 2)
        self.assertIn("Hot component", messages[-1])
        issue = store.session.team.issues[0]
        service.update_issue("owner", "session", issue.id,
                             UpdateIssueRequest(status="resolved", resolution="Connector repaired"))
        self.assertEqual(issue.resolution, "Connector repaired")
        self.assertEqual(issue.status, "resolved")
        self.assertGreater(issue.updated_at, 0)
        with self.assertRaises(PermissionError):
            service.update_issue("other", "session", issue.id, UpdateIssueRequest(status="open"))

    async def test_background_storage_failure_is_retrieved_and_retryable(self):
        store = Store()
        execute = AsyncMock(return_value=WorkerResult(summary="reviewed"))
        service = WorkbenchTeamService(store, None, {"diagnosis": execute}, automatic_interval=0)
        with patch.object(store, "remember", side_effect=OSError("private storage path")):
            await service.start("owner", "session", RunTeamRequest())
            await asyncio.sleep(0)
            task = service._background["session"]
            self.assertTrue(task.done())
            self.assertIsInstance(task.exception(), OSError)
            self.assertFalse(store.session.team.running)
        await service.start("owner", "session", RunTeamRequest())
        await service._background["session"]
        self.assertEqual(execute.await_count, 1)

    async def test_issue_title_has_explicit_limit_and_long_run_message_is_deduplicated(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            CreateIssueRequest(title="x" * 501)
        store = Store()
        service = WorkbenchTeamService(store, None, {})
        await service.run("owner", "session", RunTeamRequest(message="x" * 1000))
        await service.run("owner", "session", RunTeamRequest(message="x" * 1000))
        self.assertEqual(len(store.session.team.issues), 1)
        self.assertEqual(len(store.session.team.issues[0].title), 500)

    async def test_specialists_start_concurrently_and_persist_isolated_failures(self):
        store = Store()
        started = set()
        barrier = asyncio.Event()

        def executor(worker):
            async def run(_session, _message):
                started.add(worker)
                if len(started) == len(WORKERS):
                    barrier.set()
                await asyncio.wait_for(barrier.wait(), 1)
                if worker == "pricing":
                    raise RuntimeError("secret provider detail")
                return WorkerResult(summary=worker)
            return run

        service = WorkbenchTeamService(store, None, {worker: executor(worker) for worker in WORKERS})
        team = await service.run("owner", "session", RunTeamRequest(message="No audio"))
        self.assertFalse(team.running)
        self.assertEqual(len(started), 5)
        self.assertEqual([task.status for task in team.tasks].count("completed"), 4)
        self.assertEqual(team.tasks[-1].summary, "team_execution_failed")
        self.assertNotIn("secret", store.saved)
        reloaded = WorkbenchSession.model_validate_json(store.saved)
        self.assertEqual(reloaded.team.issues[0].title, "No audio")
        self.assertEqual(len(reloaded.team.tasks), 5)

    async def test_duplicate_runs_and_issues_do_not_duplicate_work(self):
        store = Store()
        started, release = asyncio.Event(), asyncio.Event()

        async def execute(_session, _message):
            started.set()
            await release.wait()
            return WorkerResult(summary="done")

        service = WorkbenchTeamService(store, None, {"diagnosis": execute})
        request = CreateIssueRequest(title="No audio")
        service.issue("owner", "session", request)
        service.issue("owner", "session", request)
        first = asyncio.create_task(service.run("owner", "session", RunTeamRequest()))
        await asyncio.wait_for(started.wait(), 2)
        await service.run("owner", "session", RunTeamRequest())
        self.assertEqual(len(store.session.team.tasks), 5)
        self.assertEqual(len(store.session.team.issues), 1)
        release.set()
        await first
        self.assertEqual(store.session.team.workers[3].status, "blocked")

    async def test_search_requires_identity_and_keeps_actual_sources(self):
        store = Store()
        service = WorkbenchTeamService(store, None)
        search = AsyncMock(return_value="Risultati Web:\nTitolo: Manual\nLink: https://example.org/manual.pdf\nSnippet: candidate")
        with patch("server.features.agent_tools.web_search.tool.web_search", search):
            result = await service._schematic(store.session, "generic request")
            self.assertEqual(result.summary, "team_identity_required")
            search.assert_not_awaited()
            store.session.aliases["IC1"] = "LM3886"
            result = await service._schematic(store.session, "")
            self.assertEqual(result.evidence[0].url, "https://example.org/manual.pdf")
            self.assertIn("LM3886", search.await_args.args[0])

    async def test_owner_boundary_and_interrupted_recovery(self):
        store = Store()
        service = WorkbenchTeamService(store, None, {})
        with self.assertRaises(PermissionError):
            service.issue("other", "session", CreateIssueRequest(title="fault"))
        await service.run("owner", "session", RunTeamRequest())
        store.session.team.running = True
        store.session.team.tasks[0].status = "running"
        store.session.team.workers[0].status = "running"
        service.get("owner", "session")
        self.assertEqual(store.session.team.tasks[0].status, "failed")
        self.assertFalse(store.session.team.running)


if __name__ == "__main__":
    unittest.main()
