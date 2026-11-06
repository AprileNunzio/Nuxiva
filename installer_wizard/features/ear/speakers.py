import time

import numpy as np

import native_core

RATE = 16000
WINDOW_S = 1.5
SPLIT_FROM_S = 3.0
MAX_WINDOWS = 8
CHANGE = 0.55


class SpeakerContext:

    def __init__(self, voiceprints) -> None:
        self.voiceprints = voiceprints
        tracker = native_core.symbol("RustVoiceTracker")
        if tracker is None:
            native_core.python_fallback("ear.speakers")
        self.tracker = tracker() if tracker is not None else None
        self.split = native_core.symbol("ear_split_turns")

    def _windows(self, audio: np.ndarray) -> list[np.ndarray]:
        size = int(WINDOW_S * RATE)
        if len(audio) < SPLIT_FROM_S * RATE:
            return []
        count = min(MAX_WINDOWS, max(2, int((len(audio) - size) / (size / 2)) + 1))
        hop = (len(audio) - size) / max(1, count - 1)
        return [audio[int(i * hop):int(i * hop) + size] for i in range(count)]

    def dominant(self, audio: np.ndarray) -> tuple[np.ndarray, bool]:
        windows = self._windows(audio)
        if self.split is None or not windows:
            return audio, False
        embedded = [(w, self.voiceprints.embed(w)) for w in windows]
        usable = [(w, e) for w, e in embedded if e is not None]
        if len(usable) < 2:
            return audio, False
        labels = self.split([e.astype(np.float32).tolist() for _, e in usable], CHANGE)
        if len(set(labels)) < 2:
            return audio, False
        main = max(set(labels), key=labels.count)
        parts = [w for (w, _), label in zip(usable, labels) if label == main]
        return np.concatenate(parts), True

    def identify(self, audio: np.ndarray, alone: str | None) -> tuple[str | None, float, dict]:
        speech, mixed = self.dominant(audio)
        probe = self.voiceprints.embed(speech)
        slug, score = self.voiceprints.identify(probe)
        if probe is not None and alone and not mixed and slug in (None, alone):
            self.voiceprints.add(alone, probe, "ascolto")
        info: dict = {"mixed_speakers": mixed}
        if self.tracker is not None and probe is not None:
            info.update(self.tracker.observe(np.asarray(probe, dtype=np.float32).tolist(), time.time(), slug) or {})
        return slug, score, info

    def active(self) -> int:
        return self.tracker.active(time.time()) if self.tracker is not None else 0
