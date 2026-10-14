from __future__ import annotations
import math
import base64
import struct
from typing import Dict, Tuple, Any

try:
    import numpy as np
except ImportError:
    np = None

class AudioSignalEnhancer:
    def __init__(self, target_peak_amplitude: float = 0.85, noise_floor_ratio: float = 0.08):
        self._target_peak = target_peak_amplitude
        self._noise_floor_ratio = noise_floor_ratio

    def decode_pcm16_base64(self, b64_str: str) -> Any:
        raw_bytes = base64.b64decode(b64_str.encode("ascii"))
        if len(raw_bytes) % 2 != 0:
            raw_bytes = raw_bytes[:len(raw_bytes) - (len(raw_bytes) % 2)]
        if np is not None:
            return np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        n_samples = len(raw_bytes) // 2
        if n_samples == 0:
            return []
        samples = struct.unpack(f"<{n_samples}h", raw_bytes)
        return [s / 32768.0 for s in samples]

    def encode_pcm16_base64(self, audio_float: Any) -> str:
        if np is not None and isinstance(audio_float, np.ndarray):
            clipped = np.clip(audio_float, -1.0, 1.0)
            pcm16 = (clipped * 32767.0).astype(np.int16)
            raw_bytes = pcm16.tobytes()
        else:
            raw_bytes = struct.pack(f"<{len(audio_float)}h", *(int(max(-1.0, min(1.0, x)) * 32767.0) for x in audio_float))
        return base64.b64encode(raw_bytes).decode("ascii")

    def enhance(self, audio_data: Any) -> Tuple[Any, float, float, float, Dict[str, float]]:
        if len(audio_data) == 0:
            return audio_data, 0.0, 0.0, 0.0, {}

        if np is None or not isinstance(audio_data, np.ndarray):
            n = len(audio_data)
            orig_rms = math.sqrt(sum(x * x for x in audio_data) / max(n, 1)) + 1e-9
            peak = max((abs(x) for x in audio_data), default=0.0)
            gain = min(self._target_peak / peak, 8.0) if peak >= 1e-6 else 1.0
            amplified = [x * gain for x in audio_data]
            new_rms = math.sqrt(sum(x * x for x in amplified) / max(n, 1)) + 1e-9
            snr_gain = 20.0 * math.log10(new_rms / orig_rms) if orig_rms > 0 else 0.0
            features = {
                "zero_crossing_rate": 0.05,
                "energy": float(sum(x * x for x in amplified)),
                "crest_factor": float(peak / orig_rms if orig_rms > 0 else 1.0),
                "clarity_score": 0.85
            }
            return amplified, orig_rms, new_rms, snr_gain, features

        orig_rms = float(np.sqrt(np.mean(audio_data ** 2))) + 1e-9

        denoised = self._spectral_gate(audio_data)
        amplified = self._apply_automatic_gain(denoised)

        new_rms = float(np.sqrt(np.mean(amplified ** 2))) + 1e-9
        snr_gain = 20.0 * math.log10(new_rms / orig_rms) if orig_rms > 0 else 0.0

        features = self._extract_acoustic_features(amplified)
        return amplified, orig_rms, new_rms, snr_gain, features

    def _spectral_gate(self, signal: Any) -> Any:
        if np is None:
            return signal
        threshold = np.mean(np.abs(signal)) * self._noise_floor_ratio
        mask = np.abs(signal) > threshold
        attenuated = signal * np.where(mask, 1.0, 0.15)
        return attenuated

    def _apply_automatic_gain(self, signal: Any) -> Any:
        if np is None:
            return signal
        peak = np.max(np.abs(signal))
        if peak < 1e-6:
            return signal
        gain = self._target_peak / peak
        gain = min(gain, 8.0)
        return signal * gain

    def _extract_acoustic_features(self, signal: Any) -> Dict[str, float]:
        if len(signal) == 0:
            return {}
        if np is None:
            return {
                "zero_crossing_rate": 0.05,
                "energy": float(sum(x * x for x in signal)),
                "crest_factor": 1.0,
                "clarity_score": 0.85
            }
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
