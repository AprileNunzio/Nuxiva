import asyncio
import logging
import threading
import os
import re
import time
from pathlib import Path

import numpy as np

import native_core
import wake_template
from learner import current_name
from tuning import tuning

log = logging.getLogger("nuxiva.ear")

MODELS = Path(os.environ.get("NUXIVA_WAKEWORD_MODELS", "/opt/nuxiva-ear/wakeword"))
DEFAULT_MODEL = "ehi_nuxiva"
MODEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")


def _model_candidates() -> list[str]:
    override = os.environ.get("NUXIVA_WAKEWORD_MODEL", "").strip()
    name = current_name()
    native = native_core.symbol("ear_wake_model_candidates")
    if native is not None:
        return native(name, override)
    if MODEL_RE.fullmatch(override) and ".." not in override:
        return [override]
    if name == "nuxiva":
        return [DEFAULT_MODEL]
    return [value for value in (f"ehi_{name}", name) if MODEL_RE.fullmatch(value) and ".." not in value]


def model_name() -> str:
    candidates = _model_candidates()
    return next((name for name in candidates if (MODELS / f"{name}.onnx").is_file()), candidates[-1] if candidates else "")


def template_sensitivity() -> float:
    try:
        return max(0.5, min(1.6, float(os.environ.get("NUXIVA_WAKEWORD_SENSITIVITY", "1.0"))))
    except ValueError:
        return 1.0


CHUNK = 1280
COOLDOWN = 2.0


class WakeWord:

    def __init__(self) -> None:
        self.model = None
        self._async_lock = asyncio.Lock()
        self._model_lock = threading.Lock()
        self._needs_reset = False
        self._generation = 0
        self.pending = np.zeros(0, dtype=np.int16)
        self.last_hit = 0.0
        self.score = 0.0
        self.template = None
        self.model_name = model_name()
        if os.environ.get("NUXIVA_WAKEWORD", "1") != "0":
            for candidate in _model_candidates():
                self.template = wake_template.TemplateWake.load(wake_template.model_path(MODELS, candidate), template_sensitivity())
                if self.template is not None:
                    log.info("Rilevatore della parola di attivazione addestrato sulla tua voce attivo (%s)", candidate)
                    return
        if not self.model_name:
            return
        files = [MODELS / f"{self.model_name}.onnx", MODELS / "melspectrogram.onnx", MODELS / "embedding_model.onnx"]
        if os.environ.get("NUXIVA_WAKEWORD", "1") == "0" or not all(f.exists() for f in files):
            log.info("Rilevatore istantaneo non disponibile: uso solo il riconoscimento del parlato")
            return
        try:
            from openwakeword.model import Model
            self.model = self._build(Model, files)
            log.info("Rilevatore istantaneo %s attivo (soglia %.2f)", self.model_name, tuning.wake_threshold())
        except Exception as exc:
            log.warning("Rilevatore istantaneo non avviato: %s", exc)
            self.model = None

    @staticmethod
    def _build(model_cls, files: list):
        word, mel, emb = (str(f) for f in files)
        variants = (
            {"wakeword_models": [word], "inference_framework": "onnx", "melspec_model_path": mel, "embedding_model_path": emb},
            {"wakeword_model_paths": [word], "inference_framework": "onnx", "melspec_model_path": mel, "embedding_model_path": emb},
            {"wakeword_model_paths": [word], "melspec_model_path": mel, "embedding_model_path": emb},
            {"wakeword_model_paths": [word], "melspec_onnx_model_path": mel, "embedding_onnx_model_path": emb},
            {"wakeword_models": [word], "inference_framework": "onnx"},
            {"wakeword_model_paths": [word]},
        )
        errors = []
        for kwargs in variants:
            try:
                model = model_cls(**kwargs)
                log.info("openWakeWord avviato con i parametri: %s", ", ".join(kwargs))
                return model
            except TypeError as exc:
                errors.append(str(exc))
        raise RuntimeError("nessuna combinazione di parametri accettata: " + " | ".join(errors[-2:]))

    @property
    def ready(self) -> bool:
        return self.model is not None or self.template is not None

    def feed(self, frame: np.ndarray) -> bool:
        with self._model_lock:
            if self._needs_reset:
                self._needs_reset = False
                self._reset()
            return self._feed(frame)

    def _feed(self, frame: np.ndarray) -> bool:
        if self.template is not None:
            hit = self.template.feed(frame)
            self.score = self.template.score
            return hit
        if self.model is None:
            return False
        pcm = (np.clip(frame, -1, 1) * 32767).astype(np.int16)
        self.pending = np.concatenate([self.pending, pcm])
        hit = False
        while len(self.pending) >= CHUNK:
            chunk, self.pending = self.pending[:CHUNK], self.pending[CHUNK:]
            try:
                self.score = float(self.model.predict(chunk).get(self.model_name, 0.0))
            except Exception as exc:
                log.warning("Rilevatore istantaneo disattivato dopo un errore: %s", exc)
                self.model = None
                return False
            now = time.time()
            if self.score >= tuning.wake_threshold() and now - self.last_hit > COOLDOWN:
                self.last_hit = now
                hit = True
        return hit

    async def detect(self, frame: np.ndarray) -> bool:
        if not self.ready:
            return False
        async with self._async_lock:
            generation = self._generation
            hit = await asyncio.to_thread(self.feed, frame.copy())
            return hit and generation == self._generation

    def request_reset(self) -> None:
        self._generation += 1
        self._needs_reset = True

    async def reset_async(self) -> None:
        async with self._async_lock:
            await asyncio.to_thread(self.reset)

    def reset(self) -> None:
        with self._model_lock:
            self._reset()

    def judge(self, voiceprints, enforce: bool) -> bool:
        if self.template is None:
            return True
        accepted, code = wake_template.judge(self.template, voiceprints, enforce)
        if not accepted:
            log.info("Attivazione scartata dopo il controllo del parlante: %s", code)
        return accepted

    def _reset(self) -> None:
        if self.template is not None:
            self.template.reset()
        if self.model is not None:
            self.model.reset()
        self.pending = np.zeros(0, dtype=np.int16)
