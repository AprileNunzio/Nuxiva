import asyncio
import logging
import threading
import os
import re
import time
from pathlib import Path

import numpy as np

from tuning import tuning

log = logging.getLogger("nuxiva.ear")

MODELS = Path(os.environ.get("NUXIVA_WAKEWORD_MODELS", "/opt/nuxiva-ear/wakeword"))
DEFAULT_MODEL = "ehi_nuxiva"
MODEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")


def model_name() -> str:
    name = os.environ.get("NUXIVA_WAKEWORD_MODEL", "").strip()
    if name and MODEL_RE.fullmatch(name) and ".." not in name:
        return name
    assist_name = os.environ.get("NUXIVA_ASSISTANT_NAME", "").strip().lower()
    clean = re.sub(r"^(?:hey|hei|ehi|hi|ok|okay)\s+", "", assist_name).strip()
    if clean and clean != "nuxiva":
        custom = f"ehi_{clean}"
        if (MODELS / f"{custom}.onnx").exists():
            return custom
        return clean
    return DEFAULT_MODEL


MODEL_NAME = model_name()
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
        assist_name = os.environ.get("NUXIVA_ASSISTANT_NAME", "").strip().lower()
        clean = re.sub(r"^(?:hey|hei|ehi|hi|ok|okay)\s+", "", assist_name).strip()
        if clean and clean != "nuxiva" and MODEL_NAME == DEFAULT_MODEL:
            return
        files = [MODELS / f"{MODEL_NAME}.onnx", MODELS / "melspectrogram.onnx", MODELS / "embedding_model.onnx"]
        if os.environ.get("NUXIVA_WAKEWORD", "1") == "0" or not all(f.exists() for f in files):
            log.info("Rilevatore istantaneo non disponibile: uso solo il riconoscimento del parlato")
            return
        try:
            from openwakeword.model import Model
            self.model = self._build(Model, files)
            log.info("Rilevatore istantaneo «Ehi, Nuxiva» attivo (soglia %.2f)", tuning.wake_threshold())
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
        return self.model is not None

    def feed(self, frame: np.ndarray) -> bool:
        with self._model_lock:
            if self._needs_reset:
                self._needs_reset = False
                self._reset()
            return self._feed(frame)

    def _feed(self, frame: np.ndarray) -> bool:
        if self.model is None:
            return False
        pcm = (np.clip(frame, -1, 1) * 32767).astype(np.int16)
        self.pending = np.concatenate([self.pending, pcm])
        hit = False
        while len(self.pending) >= CHUNK:
            chunk, self.pending = self.pending[:CHUNK], self.pending[CHUNK:]
            try:
                self.score = float(self.model.predict(chunk).get(MODEL_NAME, 0.0))
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
        if self.model is None:
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

    def _reset(self) -> None:
        if self.model is not None:
            self.model.reset()
        self.pending = np.zeros(0, dtype=np.int16)
