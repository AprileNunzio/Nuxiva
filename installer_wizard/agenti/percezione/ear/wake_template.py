import logging
import os
import re
from pathlib import Path

import numpy as np

import native_core

log = logging.getLogger("nuxiva.ear.wake")
SUFFIX = ".nxwk"
MAX_MODEL = 2 * 1024 * 1024
MAX_TAKES = 10
MAX_TAKE_BYTES = 16000 * 2 * 4
MIN_WAKE = 0.3
NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")


def available() -> bool:
    return native_core.symbol("wake_enroll") is not None and native_core.symbol("RustWakeword") is not None


def candidates(name: str, override: str = "") -> list[str]:
    native = native_core.symbol("ear_wake_model_candidates")
    if native is not None:
        return list(native(name, override))
    override = override.strip()
    if NAME_RE.fullmatch(override) and ".." not in override:
        return [override]
    name = name.strip().lower()
    if not name or name == "nuxiva":
        return ["ehi_nuxiva"]
    return [v for v in (f"ehi_{name}", name) if NAME_RE.fullmatch(v) and ".." not in v]


def model_path(directory: Path, name: str) -> Path:
    return directory / f"{name}{SUFFIX}"


def enroll(takes: list[bytes]) -> bytes:
    enroll_native = native_core.symbol("wake_enroll")
    if enroll_native is None:
        raise RuntimeError("wake.error.engine_unavailable")
    if not isinstance(takes, list) or len(takes) > MAX_TAKES or any(
            not isinstance(t, (bytes, bytearray)) or len(t) > MAX_TAKE_BYTES for t in takes):
        raise ValueError("wake.error.recordings")
    return bytes(enroll_native([bytes(t) for t in takes]))


def save(path: Path, data: bytes) -> None:
    detector = native_core.symbol("RustWakeword")
    if detector is None:
        raise RuntimeError("wake.error.engine_unavailable")
    detector(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


class TemplateWake:
    def __init__(self, data: bytes, sensitivity: float = 1.0) -> None:
        self.engine = native_core.symbol("RustWakeword")(data, sensitivity, 1500)
        self.score = 0.0
        self.pcm = np.zeros(0, dtype=np.float32)

    @classmethod
    def load(cls, path: Path, sensitivity: float = 1.0):
        if not available() or not path.is_file():
            return None
        try:
            if path.stat().st_size > MAX_MODEL:
                raise ValueError("wake.error.model")
            return cls(path.read_bytes(), sensitivity)
        except (OSError, ValueError) as exc:
            log.warning("Modello della parola di attivazione non utilizzabile (%s)", exc)
            return None

    def feed(self, frame: np.ndarray) -> bool:
        pcm = (np.clip(frame, -1, 1) * 32767).astype("<i2")
        hits = self.engine.push(pcm.tobytes())
        if not hits:
            self.score = 0.0
            return False
        best = max(hits, key=lambda hit: hit[0])
        self.score = float(best[0])
        self.pcm = np.frombuffer(best[2], dtype="<i2").astype(np.float32) / 32768.0
        return True

    def reset(self) -> None:
        self.engine.reset()
        self.score = 0.0


def judge(wake: TemplateWake, voiceprints, enforce: bool) -> tuple[bool, str]:
    decide = native_core.symbol("wake_decide")
    kind, score = "unavailable", 0.0
    if enforce and voiceprints.ready and len(voiceprints.samples) > 0 and wake.pcm.size:
        probe = voiceprints.embed(wake.pcm)
        if probe is not None:
            verdict = voiceprints.verdict(probe)
            kind = "authorized" if verdict.get("slug") else ("ambiguous" if verdict.get("ambiguous") else "unknown")
            score = max(0.0, min(1.0, float(verdict.get("score") or 0.0)))
    accepted, code, _ = decide(float(wake.score), kind, score, False, MIN_WAKE)
    return accepted, code
