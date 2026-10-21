"""Concurrent work orders, with explicit capability and evidence boundaries."""
import asyncio
import hashlib
import json
import re
import time
import uuid
from typing import Awaitable, Callable, Dict, Optional

from server.features.repair_workbench.session_requests import ChatRequest
from server.features.repair_workbench.team_models import (
    CreateIssueRequest, RunTeamRequest, TeamEvidence, TeamTask, TeamWorker,
    UpdateIssueRequest, WorkbenchIssue, WorkerResult,
)

WORKERS = ("board_identification", "schematic_search", "diagnosis", "component_3d", "pricing")
Executor = Callable[[object, str], Awaitable[WorkerResult]]


class WorkbenchTeamService:
    def __init__(self, workbench, collaboration, executors: Optional[Dict[str, Executor]] = None,
                 automatic_interval: float = 30):
        self.workbench = workbench
        self.collaboration = collaboration
        self.executors = executors if executors is not None else {
            "board_identification": self._identify,
            "schematic_search": self._schematic,
            "pricing": self._pricing,
            "diagnosis": self._diagnose,
        }
        self._locks: Dict[str, asyncio.Lock] = {}
        self._background: Dict[str, asyncio.Task] = {}
        self._automatic: Dict[str, asyncio.Task] = {}
        self._pending: Dict[str, str] = {}
        self._automatic_interval = automatic_interval

    async def start(self, owner, session_id, request: RunTeamRequest):
        session = self.get(owner, session_id)
        current = self._background.get(session_id)
        if current is None or current.done():
            self._background[session_id] = asyncio.create_task(self.run(owner, session_id, request))
            self._background[session_id].add_done_callback(
                lambda task: self._recover_background(session, task))
            # run() persists all work orders before its first await.
            await asyncio.sleep(0)
        return session.team

    def _recover_background(self, session, task):
        # Retrieve exceptions so a provider/storage failure cannot become an
        # unhandled task or leave the operator looking at a permanent spinner.
        failed = task.cancelled() or task.exception() is not None
        if failed:
            for item in session.team.tasks:
                if item.status == "running":
                    item.status, item.summary = "failed", "team_interrupted"
            for worker in session.team.workers:
                if worker.status == "running":
                    worker.status, worker.summary = "failed", "team_interrupted"
            session.team.running = False
            try:
                self.workbench.remember(session)
            except Exception:
                pass  # The next observation/run retries after storage recovers.

    async def observe(self, owner, session_id):
        session = self.get(owner, session_id)
        self._collect_observed_issues(session)
        if not (session.popups or session.dossier.title or session.dossier.summary
                or session.team.issues):
            return session.team
        self._schedule(owner, session)
        self.workbench.remember(session)
        return session.team

    @staticmethod
    def _context_key(session):
        # Ignore tracking coordinates and prose variation: moving the same board
        # must not launch five fresh work orders on every analyzed frame.
        context = {
            "board": [session.dossier.title, session.dossier.board_kind],
            "components": sorted((p.key, p.category.value, p.health.value) for p in session.popups),
            "aliases": sorted(session.aliases.items()),
            "issues": sorted((i.id, i.status) for i in session.team.issues),
        }
        return hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()

    def _schedule(self, owner, session):
        key = self._context_key(session)
        if key == session.team.last_context_key:
            return
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return  # Sync import/maintenance callers do not own an event loop.
        session_id = session.session_id
        self._pending[session_id] = key
        current = self._automatic.get(session_id)
        if current is None or current.done():
            task = asyncio.create_task(self._drain(owner, session_id))
            self._automatic[session_id] = task
            task.add_done_callback(lambda completed: self._recover_background(session, completed))

    async def _drain(self, owner, session_id):
        while session_id in self._pending:
            session = self.get(owner, session_id)
            delay = self._automatic_interval - (time.time() - session.team.last_run_at)
            if delay > 0:
                await asyncio.sleep(delay)
            current = self._background.get(session_id)
            if current is not None and not current.done():
                await current
            key = self._pending.pop(session_id)
            if key == session.team.last_context_key:
                continue
            await self.start(owner, session_id, RunTeamRequest())
            await self._background[session_id]
            session.team.last_context_key = key
            self.workbench.remember(session)

    def get(self, owner, session_id):
        session = self.workbench.get(owner, session_id)
        if not session.team.workers:
            session.team.workers = [TeamWorker(id=worker) for worker in WORKERS]
        # An interrupted process must never leave a perpetual running indicator.
        if session.team.running and not self._locks.get(session_id, asyncio.Lock()).locked():
            for task in session.team.tasks:
                if task.status == "running":
                    task.status = "failed"
                    task.summary = "team_interrupted"
            for worker in session.team.workers:
                if worker.status == "running":
                    worker.status, worker.summary = "failed", "team_interrupted"
            session.team.running = False
            self.workbench.remember(session)
        return session

    def issue(self, owner, session_id, request: CreateIssueRequest):
        session = self.get(owner, session_id)
        self._add_issue(session, request.title, "operator", request.severity)
        self.workbench.remember(session)
        self._schedule(owner, session)
        return session.team

    def update_issue(self, owner, session_id, issue_id, request: UpdateIssueRequest):
        session = self.get(owner, session_id)
        issue = next((item for item in session.team.issues if item.id == issue_id), None)
        if issue is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Issue not found")
        issue.status, issue.resolution = request.status, request.resolution
        issue.updated_at = time.time()
        self.workbench.remember(session)
        if request.status == "open":
            self._schedule(owner, session)
        return session.team

    def _collect_observed_issues(self, session):
        labels = {
            "it": {"suspect": "possibile anomalia da verificare", "fault": "possibile guasto da verificare"},
            "en": {"suspect": "possible anomaly to verify", "fault": "possible fault to verify"},
            "es": {"suspect": "posible anomalía por verificar", "fault": "posible avería por verificar"},
            "fr": {"suspect": "anomalie possible à vérifier", "fault": "panne possible à vérifier"},
        }.get(session.language, {"suspect": "possible anomaly to verify", "fault": "possible fault to verify"})
        for popup in session.popups:
            if popup.health.value in {"suspect", "fault"}:
                self._add_issue(session, f"{popup.key}: {labels[popup.health.value]}", "observation",
                                "high" if popup.health.value == "fault" else "medium")

    @staticmethod
    def _add_issue(session, title, source, severity="medium"):
        title = CreateIssueRequest(title=title.strip()[:500]).title
        if any(issue.title.casefold() == title.casefold()
               for issue in session.team.issues):
            return
        session.team.issues.append(WorkbenchIssue(
            id=uuid.uuid4().hex, title=title, source=source, severity=severity,
            created_at=time.time(),
        ))
        session.team.issues = session.team.issues[-100:]

    async def run(self, owner, session_id, request: RunTeamRequest):
        session = self.get(owner, session_id)
        lock = self._locks.setdefault(session_id, asyncio.Lock())
        if lock.locked():
            return session.team
        async with lock:
            if request.message:
                self._add_issue(session, request.message, "operator")
            self._collect_observed_issues(session)
            # The coordinator routes evidence to specialists; high severity issues come first.
            rank = {"high": 0, "medium": 1, "low": 2}
            issues = sorted((i for i in session.team.issues if i.status == "open"),
                            key=lambda i: rank[i.severity])
            issue_ids = [i.id for i in issues]
            message = "\n".join(i.title for i in issues) or request.message
            context_key = self._context_key(session)
            session.team.running = True
            session.team.last_run_at = time.time()
            tasks = []
            for worker in session.team.workers:
                now = time.time()
                task = TeamTask(id=uuid.uuid4().hex, worker_id=worker.id,
                                issue_ids=issue_ids, created_at=now, updated_at=now)
                session.team.tasks.append(task)
                worker.status, worker.task_id, worker.updated_at = "running", task.id, now
                tasks.append((worker, task))
            session.team.tasks = session.team.tasks[-100:]
            self.workbench.remember(session)
            try:
                await asyncio.gather(*(self._execute(session, worker, task, message)
                                       for worker, task in tasks), return_exceptions=True)
                session.team.last_context_key = context_key
            finally:
                session.team.running = False
                self.workbench.remember(session)
        return session.team

    async def _execute(self, session, worker, task, message):
        try:
            executor = self.executors.get(worker.id)
            result = (await asyncio.wait_for(executor(session, message), 150)
                      if executor else WorkerResult(status="blocked", summary="team_capability_unavailable"))
            task.status, task.summary, task.evidence = result.status, result.summary, result.evidence
        except asyncio.CancelledError:
            task.status, task.summary = "failed", "team_interrupted"
            raise
        except Exception:
            # Provider internals may contain credentials. Keep them out of public logs.
            task.status, task.summary = "failed", "team_execution_failed"
        finally:
            task.updated_at = time.time()
            worker.status, worker.summary, worker.updated_at = task.status, task.summary, task.updated_at
            self.workbench.remember(session)

    async def _diagnose(self, session, message):
        if not message and not session.dossier.summary:
            return WorkerResult(status="blocked", summary="team_context_required")
        result = await self.collaboration.chat(session.owner_id, session.session_id, ChatRequest(
            message=message or session.dossier.summary,
        ))
        return WorkerResult(summary=result["reply"].get("text") or "")

    @staticmethod
    def _identity(session):
        # An operator-taught label is an explicit search seed. Generic visual guesses
        # (resistor, unknown PCB, etc.) cannot establish the identity of a board.
        labels = list(session.aliases.values())
        title = session.dossier.title
        candidates = labels + [title]
        return next((v for v in candidates if re.search(r"[A-Za-z]{2,}[\s_-]*\d{2,}|\d{2,}[A-Za-z]", v)), "")

    async def _search(self, session, suffix):
        identity = self._identity(session)
        if not identity:
            return WorkerResult(status="blocked", summary="team_identity_required")
        from server.features.agent_tools.web_search.tool import web_search
        text = await web_search(f"{identity} {suffix}", max_results=5)
        urls = re.findall(r"^Link: (https?://\S+)", text, flags=re.MULTILINE)
        if not urls:
            return WorkerResult(status="blocked", summary="team_no_search_evidence")
        return WorkerResult(
            summary=text[:1200],
            evidence=[TeamEvidence(url=url, title=identity) for url in urls[:10]],
        )

    async def _identify(self, session, _message):
        return await self._search(session, "board manufacturer datasheet")

    async def _schematic(self, session, _message):
        return await self._search(session, "schematic service manual circuit diagram")

    async def _pricing(self, session, _message):
        # Search leads are not quotes, verified compatibility, stock, or current prices.
        return await self._search(session, "replacement board component price supplier")
