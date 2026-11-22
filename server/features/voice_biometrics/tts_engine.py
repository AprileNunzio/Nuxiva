import logging
import os
import shutil
import subprocess
import wave
from io import BytesIO
from typing import Tuple

import numpy as np

from server.features.voice_biometrics.audio_contracts import TTSRequest
from server.features.voice_engine.vocal_profiles.registry import vocal_profile_registry
from server.features.human_affective_engine.adaptive_response_orchestrator import adaptive_response_orchestrator

logger = logging.getLogger("nuxiva.tts")

MODELS_DIR = os.environ.get("NUXIVA_TTS_MODELS_DIR", "/app/data/models/tts")
SAMPLE_RATE = 22050


def apply_vocal_modulation(
    raw_pcm16: bytes,
    sample_rate: int = SAMPLE_RATE,
    volume_db: float = 0.0,
    whisper_mode: bool = False,
) -> bytes:
    """
    Applica modulazione acustica reale sul PCM16 in uscita:
    - Guadagno in dB (es. -8 dB per sussurro o tono raccolto) con protezione soft-clipping.
    - Modalità sussurro (whisper_mode): attenua le basse frequenze fondamentali e aggiunge
      una leggera componente d'aria soffusa proporzionale all'inviluppo vocale.
    """
    if not raw_pcm16:
        return raw_pcm16

    samples = np.frombuffer(raw_pcm16, dtype="<i2").astype(np.float32) / 32768.0
    if len(samples) == 0:
        return raw_pcm16

    if whisper_mode:
        # Attenuate strong low-frequency glottal fundamental (< 450 Hz) and soften upper harshness
        spec = np.fft.rfft(samples)
        freqs = np.fft.rfftfreq(len(samples), d=1.0 / sample_rate)
        low_mask = freqs < 450.0
        spec[low_mask] *= 0.35
        whispered = np.fft.irfft(spec, n=len(samples)).astype(np.float32)

        # Modulate gentle breathy airflow with the speech amplitude envelope
        win = max(1, int(sample_rate * 0.02))
        env = np.convolve(np.abs(samples), np.ones(win, dtype=np.float32) / win, mode="same")
        rng = np.random.default_rng(7)
        air = rng.standard_normal(len(samples)).astype(np.float32) * 0.08 * env
        samples = (whispered * 0.85) + air

    if abs(volume_db) > 1e-3:
        gain = float(10.0 ** (volume_db / 20.0))
        samples = samples * gain

    samples = np.clip(samples, -0.98, 0.98)
    return (samples * 32767.0).astype("<i2").tobytes()


class PiperTTSEngine:
    def __init__(self, models_dir: str = MODELS_DIR, executable_path: str = "piper"):
        self.models_dir = models_dir
        self.executable_path = executable_path

    def _model_path(self, voice_profile: str) -> str:
        return os.path.join(self.models_dir, f"{voice_profile}.onnx")

    def is_available(self, voice_profile: str = "it_IT-paola-medium") -> bool:
        return shutil.which(self.executable_path) is not None and os.path.exists(self._model_path(voice_profile))

    def resolve_modulation(self, request: TTSRequest) -> Tuple[float, float, bool]:
        speed = request.speed
        volume_db = request.volume_db if request.volume_db is not None else 0.0
        whisper_mode = bool(request.whisper_mode) if request.whisper_mode is not None else False

        if request.user_id:
            mod = adaptive_response_orchestrator.get_voice_modulation_params(request.user_id)
            if request.speed == 1.0 and "speed" in mod:
                speed = float(mod["speed"])
            if request.volume_db is None and "volume_db" in mod:
                volume_db = float(mod["volume_db"])
            if request.whisper_mode is None and "whisper_mode" in mod:
                whisper_mode = bool(mod["whisper_mode"])

        return speed, volume_db, whisper_mode

    def generate_speech_raw(self, text: str, voice_profile: str, speed: float = 1.0) -> bytes:
        prepared_text = vocal_profile_registry.get_profile("piper").prepare_for_synthesis(text)
        model_path = self._model_path(voice_profile)
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"TTS model not found: {model_path}")

        command = [
            self.executable_path,
            "--model", model_path,
            "--length_scale", str(round(1.0 / max(speed, 0.1), 3)),
            "--output_raw",
        ]
        process = subprocess.run(command, input=prepared_text.encode("utf-8"), capture_output=True, timeout=60)
        if process.returncode != 0:
            raise RuntimeError(f"Piper failed: {process.stderr.decode(errors='ignore')[:200]}")
        return process.stdout

    def synthesize_speech_wav(self, request: TTSRequest) -> bytes:
        speed, volume_db, whisper_mode = self.resolve_modulation(request)
        try:
            raw = self.generate_speech_raw(request.text, request.voice_profile, speed)
        except (FileNotFoundError, RuntimeError, subprocess.TimeoutExpired) as exc:
            logger.warning("TTS unavailable: %s", exc)
            return b""

        raw = apply_vocal_modulation(raw, SAMPLE_RATE, volume_db=volume_db, whisper_mode=whisper_mode)

        buffer = BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(raw)
        return buffer.getvalue()


tts_engine = PiperTTSEngine()
