import native_core

JUMP_MS = 3_000
MAX_OBSERVATIONS = 3
LIMIT = 1 << 50


def _div(value: int, by: int) -> int:
    return value // by if value >= 0 else -((-value) // by)


class PySongClock:

    def __init__(self) -> None:
        self.origin: int | None = None
        self.pending: int | None = None
        self.count = 0

    def reset(self) -> None:
        self.origin, self.pending, self.count = None, None, 0

    def observe(self, wall_ms: int, pos_ms: int) -> tuple[int, bool, int]:
        candidate = max(-LIMIT, min(LIMIT, wall_ms)) - max(-LIMIT, min(LIMIT, pos_ms))
        if self.origin is None:
            self.origin, self.count, self.pending = candidate, 1, None
            return candidate, True, 0
        error = candidate - self.origin
        if abs(error) <= JUMP_MS:
            step = _div(error, min(self.count, MAX_OBSERVATIONS) + 1)
            self.origin += step
            self.count = min(self.count + 1, MAX_OBSERVATIONS)
            self.pending = None
            return self.origin, False, step
        if self.pending is not None and abs(candidate - self.pending) <= JUMP_MS:
            before = self.origin
            self.origin = self.pending + _div(candidate - self.pending, 2)
            self.count, self.pending = 2, None
            return self.origin, True, self.origin - before
        self.pending = candidate
        return self.origin, False, 0


class SongClock:

    def __init__(self, engine=None) -> None:
        if engine is None:
            native = native_core.symbol("RustSongClock")
            if native is None:
                native_core.python_fallback("music.clock")
            engine = native() if native is not None else PySongClock()
        self.engine = engine

    def observe(self, wall: float, position: float) -> tuple[float, bool]:
        origin, jumped, _ = self.engine.observe(int(round(wall * 1000)), int(round(position * 1000)))
        return origin / 1000, bool(jumped)

    def reset(self) -> None:
        self.engine.reset()
