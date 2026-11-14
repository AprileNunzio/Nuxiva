import json
import logging
import os
import threading
import time
from pathlib import Path

log = logging.getLogger("nuxiva.team.shadow")

SCHEMA = 1
KEEP_DAYS = 60
WINDOW_DAYS = 14
MIN_CLEAN_DAYS = 3
FIELDS = ("compared", "matched", "mismatched", "errors")
MAX_COUNT = 10**12
FLUSH_EVERY = 25
FLUSH_SECONDS = 30.0


def _count(value) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= MAX_COUNT else 0


def _day(moment: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(moment))


class ShadowStore:
    def __init__(self, path: Path | None, clock=time.time) -> None:
        self.path = path
        self._clock = clock
        self._lock = threading.Lock()
        self._dirty = 0
        self._flushed = clock()
        self.totals = dict.fromkeys(FIELDS, 0)
        self.first_at = 0.0
        self.last_at = 0.0
        self.streak = 0
        self.days: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if self.path is None or not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("schema") != SCHEMA:
                raise ValueError("schema")
            self.totals = {k: _count(data.get("totals", {}).get(k)) for k in FIELDS}
            self.first_at = float(data.get("first_at") or 0.0)
            self.last_at = float(data.get("last_at") or 0.0)
            self.streak = _count(data.get("streak"))
            days = data.get("days", {})
            self.days = {str(d): {k: _count(v.get(k)) for k in FIELDS} for d, v in days.items() if isinstance(v, dict)}
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            log.error("Statistiche del confronto in ombra illeggibili, riparto da zero: %s", exc)
            try:
                self.path.replace(self.path.with_suffix(".bad"))
            except OSError as move_exc:
                log.error("Impossibile mettere da parte il file corrotto: %s", move_exc)
            self.totals, self.days, self.streak = dict.fromkeys(FIELDS, 0), {}, 0

    def record(self, same: bool | None = None, error: bool = False) -> None:
        now = self._clock()
        with self._lock:
            day = self.days.setdefault(_day(now), dict.fromkeys(FIELDS, 0))
            if not self.first_at:
                self.first_at = now
            self.last_at = now
            if error:
                keys = ("errors",)
            elif same is None:
                return
            else:
                keys = ("compared", "matched" if same else "mismatched")
                self.streak = self.streak + 1 if same else 0
            for key in keys:
                self.totals[key] = min(MAX_COUNT, self.totals[key] + 1)
                day[key] = min(MAX_COUNT, day[key] + 1)
            self._dirty += 1
            if self._dirty >= FLUSH_EVERY or now - self._flushed >= FLUSH_SECONDS:
                self._flush_locked(now)

    def _trim(self, now: float) -> None:
        cutoff = _day(now - KEEP_DAYS * 86400)
        self.days = {d: v for d, v in self.days.items() if d >= cutoff}

    def _flush_locked(self, now: float) -> None:
        self._dirty, self._flushed = 0, now
        if self.path is None:
            return
        self._trim(now)
        body = json.dumps({"schema": SCHEMA, "totals": self.totals, "first_at": self.first_at, "last_at": self.last_at,
                           "streak": self.streak, "days": self.days}, separators=(",", ":"), sort_keys=True)
        tmp = self.path.with_suffix(".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(body)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, self.path)
        except OSError as exc:
            log.error("Statistiche del confronto in ombra non salvate: %s", exc)

    def flush(self) -> None:
        with self._lock:
            self._flush_locked(self._clock())

    def gate(self) -> dict:
        now = self._clock()
        with self._lock:
            recent = [v for d, v in self.days.items() if d >= _day(now - WINDOW_DAYS * 86400)]
            clean = sum(1 for v in recent if v["compared"] > 0 and v["mismatched"] == 0 and v["errors"] == 0)
            diffs = sum(v["mismatched"] for v in recent)
            observed = int((now - self.first_at) // 86400) if self.first_at else 0
            return {"observed_days": observed, "clean_days": clean, "window_mismatches": diffs, "streak": self.streak,
                    "ready": observed >= WINDOW_DAYS and clean >= MIN_CLEAN_DAYS and diffs == 0}


def default_store() -> ShadowStore:
    from config import STATE_DIR
    return ShadowStore(Path(STATE_DIR) / "team" / "swarm_shadow.json")
