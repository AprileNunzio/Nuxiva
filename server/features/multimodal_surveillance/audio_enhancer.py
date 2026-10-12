import math
import base64
import numpy as np
from typing import Dict, Tuple

class AudioSignalEnhancer:
    def __init__(self, target_peak_amplitude: float = 0.85, noise_floor_ratio: float = 0.08):
        self._target_peak = target_peak_amplitude
        self._noise_floor_ratio = noise_floor_ratio

    def decode_pcm16_base64(self, b64_str: str) -> np.ndarray:
        raw_bytes = base64.b64decode(b64_str.encode("ascii"))
        if len(raw_bytes) % 2 != 0:
            raw_bytes = raw_bytes[:len(raw_bytes) - (len(raw_bytes) % 2)]
        return np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0

    def encode_pcm16_base64(self, audio_float: np.ndarray) -> str:
        clipped = np.clip(audio_float, -1.0, 1.0)
        pcm16 = (clipped * 32767.0).astype(np.int16)
        raw_bytes = pcm16.tobytes()
        return base64.b64encode(raw_bytes).decode("ascii")

    def enhance(self, audio_data: np.ndarray) -> Tuple[np.ndarray, float, float, float, Dict[str, float]]:
        if len(audio_data) == 0:
            return audio_data, 0.0, 0.0, 0.0, {}

        orig_rms = float(np.sqrt(np.mean(audio_data ** 2))) + 1e-9
        orig_peak = float(np.max(np.abs(audio_data))) + 1e-9

        denoised = self._spectral_gate(audio_data)
        amplified = self._apply_automatic_gain(denoised)

        new_rms = float(np.sqrt(np.mean(amplified ** 2))) + 1e-9
        snr_gain = 20.0 * math.log10(new_rms / orig_rms) if orig_rms > 0 else 0.0

        features = self._extract_acoustic_features(amplified)
        return amplified, orig_rms, new_rms, snr_gain, features

    def _spectral_gate(self, signal: np.ndarray) -> np.ndarray:
        threshold = np.mean(np.abs(signal)) * self._noise_floor_ratio
        mask = np.abs(signal) > threshold
        attenuated = signal * np.where(mask, 1.0, 0.15)
        return attenuated

    def _apply_automatic_gain(self, signal: np.ndarray) -> np.ndarray:
        peak = np.max(np.abs(signal))
        if peak < 1e-6:
            return signal
        gain = self._target_peak / peak
        gain = min(gain, 8.0)
        return signal * gain

    def _extract_acoustic_features(self, signal: np.ndarray) -> Dict[str, float]:
        if len(signal) == 0:
            return {}
        zcr = float(np.mean(np.abs(np.diff(np.sign(signal)))) / 2.0)
        energy = float(np.sum(signal ** 2))
        crest_factor = float(np.max(np.abs(signal)) / (np.sqrt(np.mean(signal ** 2)) + 1e-9))
        return {
            "zero_crossing_rate": zcr,
            "energy": energy,
            "crest_factor": crest_factor,
            "clarity_score": float(np.clip(1.0 - (zcr * 1.5), 0.1, 1.0))
        }

audio_enhancer = AudioSignalEnhancer()
