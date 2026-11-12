import threading
from collections.abc import Callable

Encoded = tuple[int, bytes]


class SharedEncoder:
    def __init__(self, limit: int = 16) -> None:
        self._lock = threading.Lock()
        self._slots: dict[tuple, Encoded] = {}
        self._guards: dict[tuple, threading.Lock] = {}
        self._limit = limit
        self.encodes = 0

    def _fresh(self, key: tuple, current: int) -> Encoded | None:
        slot = self._slots.get(key)
        return slot if slot is not None and current > 0 and slot[0] == current else None

    def _guard(self, key: tuple) -> threading.Lock:
        with self._lock:
            guard = self._guards.get(key)
            if guard is None:
                if len(self._guards) >= self._limit:
                    raise ValueError("vision.encoder.too_many_variants")
                guard = self._guards[key] = threading.Lock()
            return guard

    def get(self, key: tuple, current: int, produce: Callable[[], Encoded]) -> Encoded:
        slot = self._fresh(key, current)
        if slot is not None:
            return slot
        with self._guard(key):
            slot = self._fresh(key, current)
            if slot is not None:
                return slot
            fid, data = produce()
            self.encodes += 1
            if data:
                with self._lock:
                    self._slots[key] = (fid, data)
            return fid, data
