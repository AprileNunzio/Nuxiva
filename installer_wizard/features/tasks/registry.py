import json
import logging
import re
import secrets
import threading
import time

from config import STATE_DIR
from sealed import write_private

log = logging.getLogger("nuxiva.tasks")
FILE = STATE_DIR / "tasks.json"
ID_RE = re.compile(r"^t[0-9a-f]{10}$")
ACTIVE = ("queued", "running")
STATES = ("queued", "running", "done", "error", "cancelled")
MAX_TASKS = 300
KEEP_DAYS = 30
WRITE_GAP = 2.0
FIELDS = {"title": 100, "stage": 120, "summary": 400, "error": 200, "detail": 300}


def _clip(value, limit: int) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


class Registry:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._items: dict[str, dict] | None = None
        self._written = 0.0
        self.cancelled: set[str] = set()

    def _load(self) -> dict[str, dict]:
        if self._items is not None:
            return self._items
        items: dict[str, dict] = {}
        try:
            rows = json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else []
        except (OSError, ValueError) as exc:
            log.error("Attività non leggibili: %s", exc)
            rows = []
        for row in rows if isinstance(rows, list) else []:
            if isinstance(row, dict) and ID_RE.fullmatch(str(row.get("id", ""))) and row.get("state") in STATES:
                if row["state"] in ACTIVE:
                    row.update(state="error", error="interrupted", stage="", updated=time.time(), finished=time.time())
                items[row["id"]] = row
        self._items = items
        return items

    def _save(self, force: bool = False) -> None:
        now = time.time()
        if not force and now - self._written < WRITE_GAP:
            return
        items = self._load()
        keep = sorted(items.values(), key=lambda r: r["updated"], reverse=True)[:MAX_TASKS]
        cutoff = now - KEEP_DAYS * 86400
        rows = [r for r in keep if r["state"] in ACTIVE or r["updated"] >= cutoff]
        try:
            write_private(FILE, json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode())
            self._written = now
        except OSError as exc:
            log.error("Attività non salvate: %s", exc)

    def start(self, kind: str, title: str, feature: str, ref: str = "", detail: str = "") -> str:
        with self._lock:
            items = self._load()
            task_id = "t" + secrets.token_hex(5)
            now = time.time()
            items[task_id] = {"id": task_id, "kind": _clip(kind, 24), "title": _clip(title, 100), "feature": _clip(feature, 32), "ref": _clip(ref, 40), "state": "running",
                              "stage": "", "detail": _clip(detail, 300), "progress": 0.0, "summary": "", "error": "", "created": now, "updated": now, "finished": 0.0,
                              "result": {}, "offer": None, "answered": False, "steps": []}
            self._save(True)
            return task_id

    def update(self, task_id: str, progress: float | None = None, steps: list | None = None, **fields) -> None:
        with self._lock:
            row = self._load().get(task_id)
            if not row or row["state"] not in ACTIVE:
                return
            for key, limit in FIELDS.items():
                if key in fields:
                    row[key] = _clip(fields[key], limit)
            if progress is not None:
                row["progress"] = round(min(1.0, max(row["progress"], float(progress))), 3)
            if steps is not None:
                row["steps"] = [{"text": _clip(s.get("text"), 120), "state": s.get("state") if s.get("state") in ("pending", "running", "done", "error") else "pending"} for s in steps[:40]]
            row["updated"] = time.time()
            self._save()

    def finish(self, task_id: str, summary: str, result: dict | None = None, offer: dict | None = None) -> None:
        with self._lock:
            row = self._load().get(task_id)
            if not row or row["state"] not in ACTIVE:
                return
            now = time.time()
            row.update(state="done", progress=1.0, stage="", summary=_clip(summary, 400), result=result or {}, offer=offer, answered=offer is None, updated=now, finished=now)
            self._save(True)

    def fail(self, task_id: str, reason: str) -> None:
        with self._lock:
            row = self._load().get(task_id)
            if not row or row["state"] not in ACTIVE:
                return
            now = time.time()
            row.update(state="error", stage="", error=_clip(reason, 200), updated=now, finished=now, answered=False)
            self._save(True)

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            row = self._load().get(task_id)
            if not row or row["state"] not in ACTIVE:
                return False
            now = time.time()
            row.update(state="cancelled", stage="", updated=now, finished=now, answered=True)
            self.cancelled.add(task_id)
            self._save(True)
            return True

    def is_cancelled(self, task_id: str) -> bool:
        return task_id in self.cancelled

    def answer(self, task_id: str) -> dict | None:
        with self._lock:
            row = self._load().get(task_id)
            if not row:
                return None
            row["answered"] = True
            row["updated"] = time.time()
            self._save(True)
            return dict(row)

    def get(self, task_id: str) -> dict | None:
        with self._lock:
            row = self._load().get(task_id)
            return dict(row) if row else None

    def rows(self) -> list[dict]:
        with self._lock:
            return [dict(r) for r in self._load().values()]


registry = Registry()
