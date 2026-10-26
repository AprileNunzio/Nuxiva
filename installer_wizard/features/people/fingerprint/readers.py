import threading
import time

from features.people.fingerprint.model import clean_label, clean_transport

FRESH_SECONDS = 180.0
MAX_READERS = 64


class Readers:
    def __init__(self) -> None:
        self._rows: dict[str, dict] = {}
        self._lock = threading.Lock()

    def seen(self, node_id: str, room: str, reader: str, transport: str, label: str, now: float | None = None, ready: bool = True) -> dict:
        now = now or time.time()
        key = f"{node_id}:{reader}"
        with self._lock:
            if key not in self._rows and len(self._rows) >= MAX_READERS:
                oldest = min(self._rows, key=lambda k: self._rows[k]["at"])
                del self._rows[oldest]
            row = {"key": key, "node": node_id, "reader": reader, "room": clean_label(room, 60),
                   "transport": clean_transport(transport), "label": clean_label(label) or reader, "ready": ready, "at": now}
            self._rows[key] = row
        return row

    def get(self, key: str, now: float | None = None) -> dict | None:
        now = now or time.time()
        with self._lock:
            row = self._rows.get(key)
        return row if row and now - row["at"] <= FRESH_SECONDS else None

    def listing(self, now: float | None = None) -> list[dict]:
        now = now or time.time()
        with self._lock:
            rows = [dict(r, online=now - r["at"] <= FRESH_SECONDS) for r in self._rows.values()]
        return sorted(rows, key=lambda r: (r["room"], r["label"]))

    def in_room(self, room: str, now: float | None = None) -> list[dict]:
        return [r for r in self.listing(now) if r["online"] and r["room"].lower() == room.lower()]

    def clear(self) -> None:
        with self._lock:
            self._rows.clear()


readers = Readers()
