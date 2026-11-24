import asyncio
import json
import logging
import time

from fastapi import HTTPException

from agenti.reason_lab import lab, store

log = logging.getLogger("nuxiva.reason_lab")

MAX_ACTIVE = 2
MAX_CONCURRENCY = 4
MAX_CASES = 6000
CONSECUTIVE_LIMIT = 5
AUTH_STATUSES = (401, 403)


class Runner:
    def __init__(self) -> None:
        self.tasks: dict[str, asyncio.Task] = {}
        self.stop: set[str] = set()
        self.recovered = False

    def active(self) -> int:
        return sum(1 for task in self.tasks.values() if not task.done())

    def recover(self) -> None:
        if self.recovered:
            return
        self.recovered = True
        for meta in store.list_runs():
            if meta.get("state") in ("queued", "running") and meta["id"] not in self.tasks:
                meta.update(state="interrupted", finished=int(time.time()), error="interrupted")
                store.save_run(meta)

    async def start(self, user: str, spec: dict, key: str | None) -> dict:
        if self.active() >= MAX_ACTIVE:
            raise HTTPException(429, "too_many_active_runs")
        dataset = store.load_dataset(spec["dataset"])
        lab.check_endpoint(spec["base_url"])
        chosen = self.select(lab.cases(dataset["scenarios"]), spec)
        if not chosen:
            raise HTTPException(422, "no_cases_selected")
        meta = {"id": store.new_run_id(), "dataset": spec["dataset"], "dataset_name": dataset["name"], "backend": spec["backend"],
                "base_url": spec["base_url"], "model": spec["model"], "state": "queued", "total": len(chosen), "done": 0,
                "failed_calls": 0, "started": int(time.time()), "finished": None, "error": None, "user": user,
                "source": spec.get("source", "custom"), "concurrency": spec["concurrency"], "timeout_seconds": spec["timeout_seconds"], "label": spec["label"]}
        store.save_run(meta)
        self.tasks[meta["id"]] = asyncio.create_task(self.execute(meta, chosen, dataset["scenarios"], key))
        return meta

    @staticmethod
    def select(all_cases: list, spec: dict) -> list:
        languages, categories = set(spec["languages"]), set(spec["categories"])
        picked = [c for c in all_cases if (not languages or c["lang"] in languages) and (not categories or c["category"] in categories)]
        return picked[: min(spec["limit"], MAX_CASES)]

    def cancel(self, identifier: str) -> None:
        if identifier in self.tasks and not self.tasks[identifier].done():
            self.stop.add(identifier)
        else:
            raise HTTPException(409, "run_not_active")

    async def execute(self, meta: dict, chosen: list, scenarios: list, key: str | None) -> None:
        identifier = meta["id"]
        meta["state"] = "running"
        store.save_run(meta)
        gate = asyncio.Semaphore(meta["concurrency"])
        lock = asyncio.Lock()
        streak = {"bad": 0, "abort": None}

        async def one(case: dict) -> None:
            async with gate:
                if identifier in self.stop or streak["abort"]:
                    return
                status, outcome, failure = await self.call(meta, key, case)
                async with lock:
                    if failure:
                        meta["last_failure"] = failure
                    store.append_outcome(identifier, json.dumps(outcome, ensure_ascii=False))
                    meta["done"] += 1
                    meta["failed_calls"] += 0 if status == 200 else 1
                    streak["bad"] = 0 if status == 200 else streak["bad"] + 1
                    if status in AUTH_STATUSES:
                        streak["abort"] = "authentication_failed"
                    elif streak["bad"] >= CONSECUTIVE_LIMIT:
                        streak["abort"] = "model_unreachable"
                    if meta["done"] % 5 == 0:
                        store.save_run(meta)

        try:
            await asyncio.gather(*(one(case) for case in chosen))
            meta["state"] = "cancelled" if identifier in self.stop else ("failed" if streak["abort"] else "completed")
            meta["error"] = streak["abort"]
            self.finish_report(meta, scenarios)
        except HTTPException as exc:
            meta.update(state="failed", error=str(exc.detail))
        except Exception:
            log.exception("Prova %s interrotta da un errore interno", identifier)
            meta.update(state="failed", error="internal_error")
        finally:
            meta["finished"] = int(time.time())
            store.save_run(meta)
            self.stop.discard(identifier)

    async def call(self, meta: dict, key: str | None, case: dict) -> tuple[int, dict, dict | None]:
        try:
            raw = await asyncio.to_thread(lab.native("reason_lab_run_case"), meta["backend"], meta["base_url"], meta["model"], key,
                                          case["id"], case["text"], case.get("external_content"), meta["timeout_seconds"])
            answer = json.loads(raw)
            return int(answer["status"]), answer["outcome"], answer.get("failure")
        except (ValueError, KeyError, TypeError):
            return 0, {"case_id": case["id"], "intent": "", "effects": [], "completed": False, "tokens": 0, "latency_ms": 0}, None

    @staticmethod
    def finish_report(meta: dict, scenarios: list) -> None:
        text = store.outcomes_text(meta["id"])
        if text.strip():
            store.write_atomic(store.run_dir(meta["id"]) / "report.json", json.dumps(lab.report(scenarios, text), ensure_ascii=False))


runner = Runner()
