import logging
import threading
import time
from datetime import datetime, timezone
from typing import Callable

from cryptography.fernet import InvalidToken
from sealed import SealedFile

from features.brain.privacy.levels import LEVELS
from features.brain.privacy.policy import ORIGINS

BLOCKED = "blocked"
BUCKETS = (*ORIGINS, BLOCKED)
KEEP_DAYS = 62
SHOWN_DAYS = 30
MAX_COUNT = 10**12
log = logging.getLogger("nuxiva.brain.privacy")


def _empty() -> dict:
    return {level: dict.fromkeys(BUCKETS, 0) for level in LEVELS}


def _clean(raw: object) -> dict:
    days = raw.get("days") if isinstance(raw, dict) and isinstance(raw.get("days"), dict) else {}
    out = {}
    for day, rows in days.items():
        if not (isinstance(day, str) and len(day) == 10 and isinstance(rows, dict)):
            continue
        clean = _empty()
        for level in LEVELS:
            row = rows.get(level) if isinstance(rows.get(level), dict) else {}
            for bucket in BUCKETS:
                value = row.get(bucket)
                if isinstance(value, int) and not isinstance(value, bool):
                    clean[level][bucket] = max(0, min(MAX_COUNT, value))
        out[day] = clean
    return {"days": out}


class PrivacyAudit:
    def __init__(self, sealed: SealedFile, clock: Callable[[], float] = time.time) -> None:
        self._sealed = sealed
        self._clock = clock
        self._lock = threading.Lock()
        self._data: dict | None = None

    def _state(self) -> dict:
        if self._data is None:
            try:
                self._data = _clean(self._sealed.load())
            except (OSError, ValueError, InvalidToken) as exc:
                log.error("Registro della privacy illeggibile, ne inizio uno nuovo: %s", type(exc).__name__)
                self._data = _clean({})
        return self._data

    def _day(self, offset: float = 0) -> str:
        return datetime.fromtimestamp(self._clock() - offset, timezone.utc).strftime("%Y-%m-%d")

    def record(self, level: str, bucket: str) -> None:
        if level not in LEVELS or bucket not in BUCKETS:
            return
        with self._lock:
            data = self._state()
            row = data["days"].setdefault(self._day(), _empty())[level]
            row[bucket] = min(MAX_COUNT, row[bucket] + 1)
            cutoff = self._day(KEEP_DAYS * 86400)
            data["days"] = {d: rows for d, rows in data["days"].items() if d >= cutoff}
            try:
                self._sealed.save(data)
            except OSError as exc:
                log.error("Registro della privacy non salvato: %s", exc)

    def summary(self) -> dict:
        with self._lock:
            days = dict(self._state()["days"])
        cutoff = self._day(SHOWN_DAYS * 86400)
        total = _empty()
        for day, rows in days.items():
            if day < cutoff:
                continue
            for level in LEVELS:
                for bucket in BUCKETS:
                    total[level][bucket] += rows[level][bucket]
        return {"days": SHOWN_DAYS, "levels": total, "today": days.get(self._day(), _empty())}
