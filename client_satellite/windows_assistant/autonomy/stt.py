import importlib.util
import logging
import threading

import numpy as np

log = logging.getLogger("nuxiva.localstt")
RATE = 16000


def available() -> bool:
    return importlib.util.find_spec("faster_whisper") is not None


class WhisperEngine:
    def __init__(self, model: str, folder: str, gpu: bool) -> None:
        self.model_name, self.folder, self.gpu = model, folder, gpu
        self.model = None
        self.lock = threading.Lock()

    def ready(self) -> bool:
        return available()

    def _load(self):
        from faster_whisper import WhisperModel
        device, compute = ("cuda", "float16") if self.gpu else ("cpu", "int8")
        try:
            return WhisperModel(self.model_name, device=device, compute_type=compute, download_root=self.folder)
        except (RuntimeError, ValueError, OSError) as exc:
            if not self.gpu:
                raise
            log.warning("GPU non utilizzabile per il riconoscimento (%s): uso la CPU", exc)
            return WhisperModel(self.model_name, device="cpu", compute_type="int8", download_root=self.folder)

    def transcribe(self, pcm: bytes, lang: str | None = None) -> tuple[str, str]:
        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        with self.lock:
            if self.model is None:
                self.model = self._load()
            segments, info = self.model.transcribe(audio, language=(lang or None), beam_size=1, vad_filter=True,
                                                   condition_on_previous_text=False)
            text = " ".join(s.text.strip() for s in segments).strip()
        return text, str(getattr(info, "language", "") or "")


def pick_engine(model: str, folder: str, gpu: bool, lang: str):
    if available():
        return WhisperEngine(model, folder, gpu)
    from autonomy.sapi_stt import SapiRecognizer
    return SapiRecognizer(lang)
