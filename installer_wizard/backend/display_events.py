import threading
import time
from collections import deque
from dataclasses import dataclass

from state import store

KEEP = 64
DEFAULT_TTL = 8.0


@dataclass(frozen=True)
class DisplayEvent:
    seq: int
    kind: str
    payload: dict
    expires: float


class DisplayEvents:

    def __init__(self) -> None:
        self._items: deque[DisplayEvent] = deque(maxlen=KEEP)
        self._seq = 0
        self._lock = threading.Lock()

    def push(self, kind: str, payload: dict, ttl: float = DEFAULT_TTL) -> int:
        with self._lock:
            self._seq += 1
            seq = self._seq
            self._items.append(DisplayEvent(seq, kind, dict(payload), time.time() + max(0.5, ttl)))
        store.touch()
        return seq

    def cursor(self) -> int:
        with self._lock:
            return self._seq

    def since(self, seq: int, now: float | None = None) -> list[DisplayEvent]:
        moment = time.time() if now is None else now
        with self._lock:
            return [e for e in self._items if e.seq > seq and e.expires > moment]

    def latest(self, kind: str, seq: int, now: float | None = None) -> DisplayEvent | None:
        found = [e for e in self.since(seq, now) if e.kind == kind]
        return found[-1] if found else None


events = DisplayEvents()


def holo(action: dict) -> int:
    return events.push("holo_action", {k: v for k, v in action.items() if v not in (None, "")})
