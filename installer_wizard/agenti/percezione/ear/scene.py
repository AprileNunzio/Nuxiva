from dataclasses import dataclass

import numpy as np

import native_core

GATE_FACTOR = 3.2
GATE_MIN = 0.010


@dataclass(frozen=True, slots=True)
class Hearing:
    voiced: bool
    kind: str
    music: bool


class SoundScene:

    def __init__(self) -> None:
        engine = native_core.symbol("RustSoundScene")
        if engine is None:
            native_core.python_fallback("ear.scene")
        self.engine = engine() if engine is not None else None

    @property
    def native(self) -> bool:
        return self.engine is not None

    def hear(self, frame: np.ndarray, rms: float, noise: float, music_playing: bool) -> Hearing:
        if self.engine is None:
            return _py_hear(rms, noise, music_playing)
        voiced, kind, music, *_ = self.engine.feed(np.asarray(frame, dtype="<f4").tobytes())
        return Hearing(bool(voiced), str(kind), bool(music))

    def reset(self) -> None:
        if self.engine is not None:
            self.engine.reset_stream()


def _py_hear(rms: float, noise: float, music_playing: bool) -> Hearing:
    voiced = rms > max(noise * GATE_FACTOR, GATE_MIN)
    return Hearing(voiced, "speech" if voiced else "silence", music_playing)
