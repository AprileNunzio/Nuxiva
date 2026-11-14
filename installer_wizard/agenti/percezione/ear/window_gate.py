import math
import struct

import barge

WINDOW_SAMPLES = 4000
MAX_PENDING_SAMPLES = 8000
MAX_FRAME_SAMPLES = 16000
QUARANTINE_WINDOWS = 8
MAX_SLUG_BYTES = 64


def native():
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustGate", None)


def _valid_slug(slug) -> bool:
    if not isinstance(slug, str) or not slug or len(slug.encode("utf-8")) > MAX_SLUG_BYTES:
        return False
    return all(33 <= ord(c) <= 126 for c in slug)


class PyGate:
    def __init__(self):
        self._audio: list[float] = []
        self._voiced_frames = 0
        self._frames = 0
        self._busy = False
        self._slug = None
        self._quarantine = 0

    def push(self, frame: bytes, voiced: bool):
        count = len(frame) // 4
        if count == 0 or count > MAX_FRAME_SAMPLES:
            return None
        samples = struct.unpack(f"<{count}f", frame[: count * 4])
        clean = all(math.isfinite(s) for s in samples)
        voiced = voiced and clean
        self._audio.extend(samples if clean else [0.0] * count)
        if len(self._audio) > MAX_PENDING_SAMPLES:
            del self._audio[: len(self._audio) - MAX_PENDING_SAMPLES]
        self._voiced_frames += int(voiced)
        self._frames += 1
        if len(self._audio) < WINDOW_SAMPLES or self._busy:
            return None
        window = self._audio[-WINDOW_SAMPLES:]
        result = (struct.pack(f"<{WINDOW_SAMPLES}f", *window), self._voiced_frames * 2 >= self._frames)
        self._audio, self._voiced_frames, self._frames, self._busy = [], 0, 0, True
        return result

    def release(self) -> None:
        self._busy = False

    def busy(self) -> bool:
        return self._busy

    def reset(self) -> None:
        self._audio, self._voiced_frames, self._frames, self._busy = [], 0, 0, False
        self._slug, self._quarantine = None, 0

    def quarantined(self) -> bool:
        return self._quarantine > 0

    def judge(self, voiced, has_match, score, runner_up, limit, music, programme, echo_cancelled, slug=None):
        verdict, margin = barge.PyBarge.judge_window(voiced, has_match, score, runner_up, limit, music, programme, echo_cancelled)
        held = self._quarantine > 0
        self._quarantine = max(0, self._quarantine - 1)
        if verdict == "broadcast":
            self._slug, self._quarantine = None, QUARANTINE_WINDOWS
            return verdict, margin
        if verdict == "known" and _valid_slug(slug) and not held:
            if self._slug == slug:
                return verdict, margin
            self._slug = slug
            return "uncertain", 0
        self._slug = None
        return "uncertain", 0


def build():
    klass = native()
    return klass() if klass is not None else PyGate()
