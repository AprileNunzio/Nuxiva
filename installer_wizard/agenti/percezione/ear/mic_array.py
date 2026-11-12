import math

import numpy as np

import native_core

MAX_CHANNELS = 8
SWITCH_DB = 3.0
SWITCH_FRAMES = 10
DEAD_RMS = 1e-5
DEAD_FRAMES = 50
DEAD_SCORE = -100.0
CLIP_LEVEL = 0.98
CLIP_PENALTY_DB = 60.0
SPEECH_RATIO = 2.0
FLOOR_FALL = 0.9
FLOOR_RISE = 1.005
LEVEL_SMOOTH = 0.92
CLIP_SMOOTH = 0.95
FLOOR_MIN = 1e-6


class _Channel:

    def __init__(self) -> None:
        self.floor = 0.003
        self.level = 0.003
        self.clip = 0.0
        self.quiet = 0
        self.primed = False

    def push(self, frame: np.ndarray) -> None:
        rms = float(np.sqrt(np.mean(frame.astype(np.float64) ** 2))) if len(frame) else 0.0
        if not self.primed:
            self.primed = True
            self.floor = self.level = max(FLOOR_MIN, rms)
        elif rms < self.floor:
            self.floor = max(FLOOR_MIN, self.floor * FLOOR_FALL + rms * (1.0 - FLOOR_FALL))
        else:
            self.floor = max(FLOOR_MIN, self.floor * FLOOR_RISE)
        if rms > self.floor * SPEECH_RATIO:
            self.level = self.level * LEVEL_SMOOTH + rms * (1.0 - LEVEL_SMOOTH)
        clipped = float(np.mean(np.abs(frame) >= CLIP_LEVEL)) if len(frame) else 0.0
        self.clip = self.clip * CLIP_SMOOTH + clipped * (1.0 - CLIP_SMOOTH)
        self.quiet = self.quiet + 1 if rms < DEAD_RMS else 0

    def score(self) -> float:
        if self.quiet >= DEAD_FRAMES:
            return DEAD_SCORE
        snr = 20.0 * math.log10((max(self.level, self.floor) + FLOOR_MIN) / (self.floor + FLOOR_MIN))
        return snr - self.clip * CLIP_PENALTY_DB


def pick_best(scores: list[float], current: int, streak: list) -> int:
    current_score = scores[current] if 0 <= current < len(scores) else DEAD_SCORE
    leader = max(range(len(scores)), key=lambda i: scores[i]) if scores else current
    leader_score = scores[leader] if scores else DEAD_SCORE
    if current_score <= DEAD_SCORE < leader_score:
        streak[:] = [leader, 0]
        return leader
    if leader == current or leader_score < current_score + SWITCH_DB:
        streak[:] = [current, 0]
        return current
    streak[:] = [leader, streak[1] + 1] if streak[0] == leader else [leader, 1]
    if streak[1] >= SWITCH_FRAMES:
        streak[:] = [leader, 0]
        return leader
    return current


class PyMicArray:

    def __init__(self, channels: int) -> None:
        if not 1 <= channels <= MAX_CHANNELS:
            raise ValueError("ear.array.channels")
        self.channels = channels
        self.reset()

    def reset(self) -> None:
        self._state = [_Channel() for _ in range(self.channels)]
        self.best = 0
        self.streak = [0, 0]

    def mix(self, frames: list[bytes]) -> tuple[bytes, int, int, list[float]]:
        if len(frames) != self.channels:
            raise ValueError("ear.array.channels")
        arrays = [np.nan_to_num(np.frombuffer(f, dtype="<f4"), nan=0.0, posinf=0.0, neginf=0.0) for f in frames]
        if not arrays[0].size or any(a.size != arrays[0].size for a in arrays):
            raise ValueError("ear.array.frame")
        for state, frame in zip(self._state, arrays):
            state.push(frame)
        scores = [s.score() for s in self._state]
        self.best = pick_best(scores, self.best, self.streak)
        return np.clip(arrays[self.best], -1.0, 1.0).astype("<f4").tobytes(), self.best, 1, scores


class MicArray:

    def __init__(self, channels: int) -> None:
        engine = native_core.symbol("RustMicArray")
        if engine is None:
            native_core.python_fallback("ear.mic_array")
            self.engine = PyMicArray(channels)
        else:
            self.engine = engine(channels)
        self.native = engine is not None
        self.best = 0
        self.fused = 1
        self.scores: list[float] = []

    def mix_pcm(self, frames: list[bytes]) -> bytes:
        floats = [(np.frombuffer(f, dtype="<i2").astype(np.float32) / 32768.0).astype("<f4").tobytes() for f in frames]
        mixed, self.best, self.fused, self.scores = self.engine.mix(floats)
        out = np.frombuffer(mixed, dtype="<f4")
        return (np.clip(out, -1.0, 32767 / 32768) * 32768.0).astype("<i2").tobytes()

    def reset(self) -> None:
        self.engine.reset()
