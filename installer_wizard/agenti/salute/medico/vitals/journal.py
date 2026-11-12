import threading
import time
from collections import deque

KEEP = 120
LEVELS = ("info", "warn", "error")
CODES = {
    "device_added", "device_removed", "key_renewed", "search_started", "search_no_nodes", "seen", "lease_taken", "lease_lost",
    "connected", "streaming", "connect_failed", "no_profiles", "disconnected", "scan_failed", "rejected_values", "cloud_ok", "cloud_error",
    "phone_paired", "code_created", "device_off", "device_on",
}


class Journal:
    def __init__(self) -> None:
        self._rows: dict[str, deque] = {}
        self._last: dict[tuple, float] = {}
        self._lock = threading.Lock()

    def add(self, slug: str, level: str, code: str, params: dict | None = None, now: float | None = None, quiet: float = 0.0) -> bool:
        if level not in LEVELS or code not in CODES:
            raise ValueError("voce di registro non valida")
        now = now or time.time()
        clean = {str(k)[:24]: str(v)[:80] for k, v in (params or {}).items()}
        key = (slug, code, tuple(sorted(clean.items())))
        with self._lock:
            if quiet and now - self._last.get(key, 0.0) < quiet:
                return False
            self._last[key] = now
            if len(self._last) > 400:
                self._last = {k: t for k, t in self._last.items() if now - t < 3600}
            self._rows.setdefault(slug, deque(maxlen=KEEP)).append({"at": now, "level": level, "code": code, "params": clean})
        return True

    def entries(self, slug: str, count: int = 60) -> list[dict]:
        with self._lock:
            rows = list(self._rows.get(slug) or [])
        return rows[-count:][::-1]

    def forget(self, slug: str) -> None:
        with self._lock:
            self._rows.pop(slug, None)


journal = Journal()
