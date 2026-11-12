import threading
import time

import native_module

HOLD_MS = 30_000
MAX_TRACKED = 1024
ORIGINS = frozenset({"user", "planner"})


def _native_class():
    return native_module.feature("RustMoveGuard")


class _ClassicGuard:

    def __init__(self, hold_ms: int) -> None:
        self.hold_ms = max(1000, hold_ms)
        self.placed: dict[str, tuple[int, int]] = {}

    def decide(self, key: str, wanted: int, origin: str, now_ms: int, alive: list[int]) -> int:
        current = self.placed.get(key)
        keep = (current is not None and current[0] != wanted and origin == "planner" and current[0] in alive
                and now_ms - current[1] < self.hold_ms)
        chosen = current[0] if keep else wanted
        if current is None or current[0] != chosen:
            if len(self.placed) >= MAX_TRACKED and key not in self.placed:
                self.placed.pop(min(self.placed, key=lambda k: self.placed[k][1]))
            self.placed[key] = (chosen, now_ms)
        return chosen

    def forget(self, alive_keys: list[str]) -> None:
        keep = set(alive_keys)
        self.placed = {k: v for k, v in self.placed.items() if k in keep}


class MoveGuard:

    def __init__(self, hold_ms: int = HOLD_MS, clock=time.time) -> None:
        native = _native_class()
        self._engine = native(hold_ms) if native else _ClassicGuard(hold_ms)
        self._clock = clock
        self._lock = threading.Lock()

    @property
    def engine(self) -> str:
        return "classic" if isinstance(self._engine, _ClassicGuard) else "rust"

    def decide(self, key: str, wanted: int, origin: str, alive: list[int]) -> int:
        if origin not in ORIGINS or not key or len(key) > 256:
            raise ValueError("invalid_move")
        with self._lock:
            return int(self._engine.decide(key, wanted, origin, int(self._clock() * 1000), list(alive)))

    def forget(self, alive_keys: list[str]) -> None:
        with self._lock:
            self._engine.forget(list(alive_keys))
