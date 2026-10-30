import asyncio
import logging
import time

from features.agency import critic, worker, workspace
from features.agency.client import AgencyRejected, AgencyUnavailable, client
from features.agency.feature import enabled
from features.agency.memory import memory
from features.agency.words import word
from features.brain.llm import BrainUnavailable

log = logging.getLogger("nuxiva.agency.runner")
TICK_SECONDS = 4.0
IDLE_SECONDS = 20.0


class Runner:
    def __init__(self) -> None:
        self.inflight: dict[tuple[str, str], asyncio.Task] = {}
        self.reconciled = False

    async def reconcile(self) -> None:
        projects = await client.call("project_list")
        for summary in projects:
            project_id = summary["project"]["id"]
            if summary["progress"]["running"] == 0:
                continue
            data = await client.call("project_get", id=project_id)
            for task in data["tasks"]:
                if task["status"] == "running" and (project_id, task["id"]) not in self.inflight:
                    await client.call("task_update", project=project_id, task=task["id"], action="interrupt")
        self.reconciled = True

    async def tick(self) -> int:
        if not self.reconciled:
            await self.reconcile()
        started = (await client.call("dispatch"))["started"]
        for item in started:
            key = (item["project"], item["task"])
            job = asyncio.create_task(self.work(*key))
            self.inflight[key] = job
            job.add_done_callback(lambda done, k=key: self.finished(k, done))
        return len(started)

    def finished(self, key: tuple[str, str], job: asyncio.Task) -> None:
        self.inflight.pop(key, None)
        if not job.cancelled() and job.exception() is not None:
            log.error("Agency task %s/%s crashed", *key, exc_info=job.exception())

    async def work(self, project_id: str, task_id: str) -> None:
        try:
            await self._work(project_id, task_id)
        except BrainUnavailable:
            await self._safe(project_id, task_id, "interrupt")
        except (workspace.WorkspaceError, OSError, KeyError) as exc:
            log.error("Agency task %s/%s failed: %s", project_id, task_id, type(exc).__name__)
            await self._safe(project_id, task_id, "fail")
        except (AgencyUnavailable, AgencyRejected) as exc:
            log.warning("Agency task %s/%s not updated: %s", project_id, task_id, type(exc).__name__)

    async def _safe(self, project_id: str, task_id: str, action: str) -> None:
        try:
            await client.call("task_update", project=project_id, task=task_id, action=action)
        except (AgencyUnavailable, AgencyRejected) as exc:
            log.warning("Agency task %s/%s %s refused: %s", project_id, task_id, action, type(exc).__name__)

    async def _work(self, project_id: str, task_id: str) -> None:
        context = memory.load(project_id)
        data = await client.call("project_get", id=project_id)
        raw = next(t for t in data["tasks"] if t["id"] == task_id)
        task = worker.task_view(raw)
        started = time.monotonic()
        _, proof, tokens = await worker.execute(context, project_id, task)
        seconds = max(1, int(time.monotonic() - started))
        await client.call("task_update", project=project_id, task=task_id, action="submit", tokens=tokens, seconds=seconds)
        verdict = await critic.review(task, proof, context["language_name"])
        if verdict.approved:
            await client.call("task_update", project=project_id, task=task_id, action="approve", tokens=verdict.tokens)
            return
        feedback = verdict.feedback or word(context["lang"], "files", "review_unclear")
        await client.call("task_update", project=project_id, task=task_id, action="rework",
                          feedback=feedback, tokens=verdict.tokens)


runner = Runner()


async def run() -> None:
    while True:
        pause = TICK_SECONDS
        if enabled():
            try:
                await runner.tick()
            except AgencyUnavailable:
                pause = IDLE_SECONDS
            except AgencyRejected as exc:
                log.warning("Agency dispatch refused: %s", exc.code)
        await asyncio.sleep(pause)
