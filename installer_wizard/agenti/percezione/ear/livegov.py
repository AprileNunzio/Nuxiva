import os
import time
from collections.abc import Callable

import earconf

MODES = ("auto", "on", "off")
MIN_INTERVAL = 0.5
MAX_INTERVAL = 2.5
SLOW_DECODE = 0.9
LOAD_LIMIT = 0.85
LOAD_CHECK = 5.0
PAUSE_FIRST = 20.0
PAUSE_MAX = 600.0
CALM_AFTER = 120.0
SMOOTHING = 0.35


def read_load() -> float:
    try:
        return os.getloadavg()[0] / max(1, os.cpu_count() or 1)
    except OSError:
        return 0.0


class LiveGovernor:

    def __init__(self, clock: Callable[[], float] = time.monotonic, load: Callable[[], float] = read_load) -> None:
        self.clock = clock
        self.load = load
        self.decode = 0.0
        self.pressure = 0.0
        self.checked = -LOAD_CHECK
        self.paused_until = 0.0
        self.pause = PAUSE_FIRST
        self.calm_since = self.clock()
        self.reason = ""

    @staticmethod
    def mode() -> str:
        return earconf.text("NUXIVA_EAR_LIVE", "auto", MODES)

    def _pressure(self, now: float) -> float:
        if now - self.checked >= LOAD_CHECK:
            self.checked = now
            self.pressure = self.load()
        return self.pressure

    def _suspend(self, now: float, reason: str) -> None:
        self.paused_until = now + self.pause
        self.pause = min(PAUSE_MAX, self.pause * 2)
        self.calm_since = now
        self.reason = reason

    def allowed(self) -> bool:
        mode = self.mode()
        if mode == "off":
            self.reason = "off"
            return False
        now = self.clock()
        if mode == "on":
            self.reason = ""
            return True
        if now < self.paused_until:
            return False
        if self._pressure(now) > LOAD_LIMIT:
            self._suspend(now, "load")
            return False
        if now - self.calm_since > CALM_AFTER:
            self.pause = PAUSE_FIRST
        self.reason = ""
        return True

    def record(self, decode_s: float) -> None:
        self.decode = decode_s if self.decode == 0.0 else self.decode * (1 - SMOOTHING) + decode_s * SMOOTHING
        if self.mode() == "auto" and self.decode > SLOW_DECODE:
            self._suspend(self.clock(), "slow")
            self.decode = 0.0

    def interval(self) -> float:
        return max(MIN_INTERVAL, min(MAX_INTERVAL, self.decode * 2.2))

    def background_ok(self) -> bool:
        if self.mode() != "auto":
            return True
        return self._pressure(self.clock()) <= LOAD_LIMIT

    def status(self) -> dict:
        now = self.clock()
        active = self.mode() == "on" or (self.mode() == "auto" and now >= self.paused_until)
        return {"mode": self.mode(), "active": active and self.mode() != "off", "reason": self.reason,
                "interval": round(self.interval(), 2), "decode_ms": int(self.decode * 1000),
                "load": round(self.pressure, 2)}
