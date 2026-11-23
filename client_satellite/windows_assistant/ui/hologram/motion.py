import math

import numpy as np

from ui.flow import Flow
from ui.hologram import palette

TICKS = 64
FLOW_STATES = frozenset(("listening", "speaking"))
BUSY_STATES = frozenset(("listening", "speaking", "thinking"))
PULSE_STATES = frozenset(("error", "alert"))
AMBIENT_REVEAL = {"offline": 0.12, "error": 0.25, "alert": 0.25}
IDLE_REVEAL = 0.34
REST_OPACITY = 0.84
TICK_ATTACK = 0.6
TICK_RELEASE = 0.08
COLOR_RATE = 0.12
REVEAL_RATE = 0.16
OPACITY_RATE = 0.14
CALM_FACTOR = 0.35


def sanitize_level(level) -> float:
    try:
        value = float(level)
    except (TypeError, ValueError):
        return 0.0
    return value if math.isfinite(value) and value > 0.0 else 0.0


class Motion:
    def __init__(self, calm: bool = False) -> None:
        self.flow = Flow()
        self.state = palette.DEFAULT
        self.phase = 0.0
        self.reveal = IDLE_REVEAL
        self.opacity = REST_OPACITY
        self.energy = 0.0
        self.color = palette.tone(self.state)
        self.ticks = np.zeros(TICKS, dtype=np.float32)
        self.calm = calm
        self._index = np.arange(TICKS, dtype=np.float32)

    @property
    def amplitude(self) -> float:
        return self.flow.amplitude

    @property
    def active(self) -> bool:
        return self.state in BUSY_STATES

    def step(self, state: str, level, hovered: bool, dt: float) -> None:
        self.state = palette.known(state)
        speed = CALM_FACTOR if self.calm else 1.0
        frames = max(0.25, min(4.0, dt * 30.0))
        self.phase += 0.1 * frames * speed
        flowing = self.state in FLOW_STATES
        self.flow.feed(sanitize_level(level) if flowing else 0.0)
        reveal = 1.0 if flowing else AMBIENT_REVEAL.get(self.state, IDLE_REVEAL)
        self.reveal += (reveal - self.reveal) * _rate(REVEAL_RATE, frames)
        busy = 1.0 if self.active else 0.0
        self.energy += (busy - self.energy) * _rate(REVEAL_RATE, frames)
        opacity = 1.0 if hovered or self.active or self.state in PULSE_STATES else REST_OPACITY
        self.opacity += (opacity - self.opacity) * _rate(OPACITY_RATE, frames)
        self.color += (palette.tone(self.state) - self.color) * _rate(COLOR_RATE, frames)
        self._spectrum(frames)

    def pulse(self) -> float:
        if self.state in PULSE_STATES:
            return 0.5 + 0.5 * math.sin(self.phase * 1.6)
        return 0.5 + 0.5 * math.sin(self.phase * 0.45)

    def _spectrum(self, frames: float) -> None:
        p = self.phase
        shape = (0.55 + 0.45 * np.sin(self._index * 1.73 + p * 2.9)) * (0.6 + 0.4 * np.sin(self._index * 0.41 - p * 1.7))
        target = np.clip(self.amplitude * (0.35 + 0.65 * shape) + 0.06 * self.reveal * shape, 0.0, 1.0)
        if self.state == "thinking":
            sweep = np.cos(self._index / TICKS * 2.0 * np.pi - p * 1.8)
            target = np.maximum(target, 0.45 * np.clip(sweep, 0.0, 1.0) ** 6)
        rate = np.where(target > self.ticks, _rate(TICK_ATTACK, frames), _rate(TICK_RELEASE, frames))
        self.ticks += (target - self.ticks) * rate


def _rate(base: float, frames: float) -> float:
    return 1.0 - (1.0 - base) ** frames
