import native_core

SOURCES = ("screen", "webcam")
THUMB_W = 9
THUMB_H = 8
SAME_BITS = 3
MIN_BASE_MS = 250
MAX_CEIL_MS = 120_000


def dhash(thumb: bytes) -> int | None:
    if len(thumb) != THUMB_W * THUMB_H:
        return None
    bits = 0
    for row in range(THUMB_H):
        line = thumb[row * THUMB_W:(row + 1) * THUMB_W]
        for col in range(THUMB_W - 1):
            if line[col] > line[col + 1]:
                bits |= 1 << (row * (THUMB_W - 1) + col)
    return bits


class PyCadence:
    def __init__(self, base_ms: int = 2000, ceiling_ms: int = 30_000) -> None:
        self.base = max(MIN_BASE_MS, min(MAX_CEIL_MS, int(base_ms)))
        self.ceiling = max(self.base, min(MAX_CEIL_MS, int(ceiling_ms)))
        self.reset()

    def reset(self) -> None:
        self.lanes = {s: {"at": None, "hash": None, "interval": self.base} for s in SOURCES}

    def _lane(self, source: str) -> dict:
        if source not in self.lanes:
            raise ValueError("capture.source")
        return self.lanes[source]

    def interval_ms(self, source: str) -> int:
        return self._lane(source)["interval"]

    def due(self, source: str, now_ms: int) -> bool:
        lane = self._lane(source)
        return lane["at"] is None or now_ms - lane["at"] >= lane["interval"]

    def admit(self, source: str, thumb: bytes, now_ms: int) -> str:
        value = dhash(thumb)
        if value is None:
            raise ValueError("capture.thumb")
        if not self.due(source, now_ms):
            return "not_due"
        lane = self._lane(source)
        lane["at"] = now_ms
        previous, lane["hash"] = lane["hash"], value
        if previous is not None and bin(previous ^ value).count("1") <= SAME_BITS:
            lane["interval"] = min(self.ceiling, lane["interval"] + lane["interval"] // 2)
            return "unchanged"
        lane["interval"] = self.base
        return "embed"


def make(base_ms: int, ceiling_ms: int):
    cls = native_core.symbol("RustCadence")
    if cls is None:
        native_core.python_fallback("vision.capture")
        return PyCadence(base_ms, ceiling_ms)
    return cls(base_ms, ceiling_ms)
