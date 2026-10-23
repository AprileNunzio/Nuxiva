import asyncio
import base64
import binascii
import secrets
from dataclasses import dataclass, field
from typing import AsyncIterator

ALLOWED = {
    ("POST", "/api/chat"), ("POST", "/api/generate"), ("POST", "/api/embed"), ("POST", "/api/embeddings"),
    ("POST", "/api/show"), ("GET", "/api/tags"), ("GET", "/api/ps"), ("GET", "/api/version"),
}
MAX_BODY = 1 << 20
MAX_CHUNK = 1 << 18
MAX_TOTAL = 64 << 20
MAX_QUEUED = 8
PICKUP_TIMEOUT = 15.0
FIRST_BYTE_TIMEOUT = 300.0
IDLE_TIMEOUT = 120.0


class RelayError(Exception):
    def __init__(self, code: str, status: int) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


@dataclass
class Job:
    node_id: str
    method: str
    path: str
    body: bytes
    id: str = field(default_factory=lambda: secrets.token_hex(16))
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    picked: asyncio.Event = field(default_factory=asyncio.Event)
    cancelled: bool = False
    received: int = 0
    finished: bool = False

    def wire(self) -> dict:
        return {"id": self.id, "method": self.method, "path": self.path,
                "body": base64.b64encode(self.body).decode("ascii")}


class ComputeRelay:
    def __init__(self) -> None:
        self.waiting: dict[str, list[Job]] = {}
        self.events: dict[str, asyncio.Event] = {}
        self.jobs: dict[str, Job] = {}

    def submit(self, node_id: str, method: str, path: str, body: bytes) -> Job:
        if (method, path) not in ALLOWED:
            raise RelayError("compute_path_not_allowed", 403)
        if len(body) > MAX_BODY:
            raise RelayError("compute_body_too_large", 413)
        if len([j for j in self.waiting.get(node_id, []) if not j.cancelled]) >= MAX_QUEUED:
            raise RelayError("compute_queue_full", 429)
        job = Job(node_id, method, path, body)
        self.jobs[job.id] = job
        self.waiting.setdefault(node_id, []).append(job)
        self.events.setdefault(node_id, asyncio.Event()).set()
        return job

    async def take(self, node_id: str, timeout: float) -> list[dict]:
        if not self.waiting.get(node_id):
            event = self.events.setdefault(node_id, asyncio.Event())
            event.clear()
            try:
                await asyncio.wait_for(event.wait(), timeout)
            except asyncio.TimeoutError:
                return []
        batch = [j for j in self.waiting.pop(node_id, []) if not j.cancelled][:4]
        for job in batch:
            job.picked.set()
        return [job.wire() for job in batch]

    def push(self, node_id: str, report: dict) -> bool:
        job = self.jobs.get(str(report.get("id") or ""))
        if job is None or job.node_id != node_id:
            raise RelayError("compute_unknown_job", 404)
        if job.finished:
            return job.cancelled
        try:
            data = base64.b64decode(str(report.get("data") or ""), validate=True)
        except (binascii.Error, ValueError):
            raise RelayError("compute_invalid_chunk", 400)
        if len(data) > MAX_CHUNK:
            raise RelayError("compute_chunk_too_large", 413)
        job.received += len(data)
        if job.received > MAX_TOTAL:
            job.cancelled = True
            job.queue.put_nowait({"error": "compute_response_too_large"})
            job.finished = True
            return True
        status = report.get("status")
        job.queue.put_nowait({"data": data, "status": status if isinstance(status, int) else None,
                              "content_type": str(report.get("content_type") or "")[:120],
                              "done": bool(report.get("done")), "error": str(report.get("error") or "")[:80]})
        job.finished = bool(report.get("done") or report.get("error"))
        return job.cancelled

    def release(self, job: Job) -> None:
        job.cancelled = not job.finished
        self.jobs.pop(job.id, None)

    async def open(self, job: Job) -> tuple[int, str, AsyncIterator[bytes]]:
        try:
            await asyncio.wait_for(job.picked.wait(), PICKUP_TIMEOUT)
        except asyncio.TimeoutError:
            self.release(job)
            raise RelayError("compute_node_unreachable", 504)
        first = await self._next(job, FIRST_BYTE_TIMEOUT)
        if first.get("error"):
            self.release(job)
            raise RelayError(first["error"], 502)
        status = int(first.get("status") or 200)
        return status, first.get("content_type") or "application/json", self._stream(job, first)

    async def _next(self, job: Job, timeout: float) -> dict:
        try:
            return await asyncio.wait_for(job.queue.get(), timeout)
        except asyncio.TimeoutError:
            self.release(job)
            raise RelayError("compute_node_timeout", 504)

    async def _stream(self, job: Job, first: dict) -> AsyncIterator[bytes]:
        item = first
        try:
            while True:
                if item.get("data"):
                    yield item["data"]
                if item.get("error"):
                    raise RelayError(item["error"], 502)
                if item.get("done"):
                    return
                item = await self._next(job, IDLE_TIMEOUT)
        finally:
            self.release(job)


relay = ComputeRelay()
