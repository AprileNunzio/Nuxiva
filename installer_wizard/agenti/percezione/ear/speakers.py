import time

import numpy as np

import native_core

RATE = 16000
WINDOW_S = 1.5
SPLIT_FROM_S = 3.0
MAX_WINDOWS = 8
CHANGE = 0.55
BOOTSTRAP_S = 2.0
ENROLLED_AT = 5
RENAMED = {"voice_known": "voice_match"}


def turn_fields(observed: dict | None) -> dict:
    return {RENAMED.get(key, key): value for key, value in (observed or {}).items()}


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
        speech, mixed, _ = self.windowed(audio)
        return speech, mixed

    def windowed(self, audio: np.ndarray) -> tuple[np.ndarray, bool, list]:
        windows = self._windows(audio)
        if self.split is None or not windows:
            return audio, False, []
        embedded = [(w, self.voiceprints.embed(w)) for w in windows]
        usable = [(w, e) for w, e in embedded if e is not None]
        verdicts = [self._window_verdict(e) for _, e in usable]
        if len(usable) < 2:
            return audio, False, verdicts
        labels = self.split([e.astype(np.float32).tolist() for _, e in usable], CHANGE)
        if len(set(labels)) < 2:
            return audio, False, verdicts
        main = max(set(labels), key=labels.count)
        parts = [w for (w, _), label in zip(usable, labels) if label == main]
        return np.concatenate(parts), True, verdicts

    def _window_verdict(self, probe: np.ndarray) -> tuple:
        result = self.voiceprints.verdict(probe)
        return result.get("slug"), float(result.get("score") or 0.0)

    def identify(self, audio: np.ndarray, alone: str | None, programme: bool = False) -> tuple[str | None, float, dict]:
        slug, score, info, _ = self.inspect(audio, alone, programme)
        return slug, score, info

    def _may_bootstrap(self, alone: str, programme: bool, seconds: float) -> bool:
        return (not programme and seconds >= BOOTSTRAP_S and self.active() <= 1
                and self.voiceprints.count(alone) < ENROLLED_AT)

    def inspect(self, audio: np.ndarray, alone: str | None, programme: bool = False) -> tuple[str | None, float, dict, np.ndarray]:
        speech, mixed, windows = self.windowed(audio)
        probe = self.voiceprints.embed(speech)
        seconds = len(speech) / RATE
        proof = self.voiceprints.attest(probe, seconds, programme, windows if mixed or len(windows) > 1 else [])
        slug, score = proof["slug"], float(proof["score"])
        if probe is not None and alone and not mixed:
            if proof["verified"] and slug == alone:
                self.voiceprints.add(alone, probe, "ascolto")
            elif slug is None and not proof["foreign"] and self._may_bootstrap(alone, programme, seconds):
                self.voiceprints.add(alone, probe, "ascolto")
        info: dict = {"mixed_speakers": mixed, "voice_verified": bool(proof["verified"]), "voice_reason": proof["reason"]}
        if self.tracker is not None and probe is not None:
            info.update(turn_fields(self.tracker.observe(np.asarray(probe, dtype=np.float32).tolist(), time.time(), slug)))
        return slug, score, info, speech

    def active(self) -> int:
        return self.tracker.active(time.time()) if self.tracker is not None else 0
