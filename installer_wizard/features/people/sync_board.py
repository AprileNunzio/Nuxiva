import re
import threading
import time

STATES = ("running", "ok", "error", "off")
MAX_ERROR = 140
MAX_PEOPLE = 64
STALE = 900.0
TIMEOUT = 120.0
REASON = re.compile(r"[^a-z_]")


class SyncBoard:
    def __init__(self) -> None:
        self._rows: dict[str, dict[str, dict]] = {}
        self._lock = threading.Lock()

    def _set(self, slug: str, key: str, **fields) -> None:
        if not slug or not key:
            return
        with self._lock:
            if slug not in self._rows and len(self._rows) >= MAX_PEOPLE:
                oldest = min(self._rows, key=lambda s: max((r["at"] for r in self._rows[s].values()), default=0.0))
                del self._rows[oldest]
            row = self._rows.setdefault(slug, {}).setdefault(key, {"key": key, "state": "ok", "at": 0.0, "ok_at": 0.0, "error": "", "reason": "", "started": 0.0})
            row.update(fields)

    def start(self, slug: str, key: str, now: float | None = None) -> None:
        now = now or time.time()
        self._set(slug, key, state="running", started=now, at=now)

    def ok(self, slug: str, key: str, now: float | None = None) -> None:
        now = now or time.time()
        self._set(slug, key, state="ok", at=now, ok_at=now, error="", reason="")

    def fail(self, slug: str, key: str, error: str, now: float | None = None, reason: str = "") -> None:
        clean = REASON.sub("", str(reason or ""))[:40]
        self._set(slug, key, state="error", at=now or time.time(), error=" ".join(str(error).split())[:MAX_ERROR], reason=clean)

    def off(self, slug: str, key: str) -> None:
        with self._lock:
            (self._rows.get(slug) or {}).pop(key, None)

    def rows(self, slug: str, now: float | None = None) -> list[dict]:
        now = now or time.time()
        with self._lock:
            rows = [dict(r) for r in (self._rows.get(slug) or {}).values()]
        out = []
        for r in rows:
            if r["state"] == "running" and now - r["started"] > TIMEOUT:
                r["state"], r["error"], r["reason"] = "error", "timeout", "timeout"
            if now - r["at"] > STALE and r["state"] != "error":
                continue
            out.append({"key": r["key"], "state": r["state"], "age": round(max(0.0, now - (r["ok_at"] or r["at"])), 1), "error": r["error"], "reason": r["reason"]})
        return sorted(out, key=lambda r: r["key"])

    def forget(self, slug: str) -> None:
        with self._lock:
            self._rows.pop(slug, None)


board = SyncBoard()
