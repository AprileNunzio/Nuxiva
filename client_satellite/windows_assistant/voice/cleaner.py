import json
import math
from typing import Any, Dict


class MediaState:
    def __init__(
        self,
        is_active: bool = False,
        source_id: str = "",
        volume_normalized: float = 0.0,
    ) -> None:
        self.is_active = is_active
        self.source_id = source_id
        self.volume_normalized = max(0.0, min(1.0, float(volume_normalized)))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_active": self.is_active,
            "source_id": self.source_id,
            "volume_normalized": self.volume_normalized,
            "stream_type": "NONE",
            "reference_energy": 0.0,
        }


class AudioCleaner:
    def __init__(self) -> None:
        self._native = None
        try:
            import nuxiva_native
            if hasattr(getattr(nuxiva_native, "RustAudioCleaner", None), "process_pcm"):
                self._native = nuxiva_native.RustAudioCleaner()
        except ImportError:
            self._native = None

    def compute_rms(self, pcm_bytes: bytes) -> float:
        if self._native is not None:
            return float(self._native.compute_rms(pcm_bytes))

        if len(pcm_bytes) < 2:
            return 0.0

        num_samples = len(pcm_bytes) // 2
        sum_sq = 0.0
        for i in range(0, len(pcm_bytes) - 1, 2):
            sample = int.from_bytes(pcm_bytes[i:i + 2], byteorder="little", signed=True)
            norm = sample / 32768.0
            sum_sq += norm * norm

        return math.sqrt(sum_sq / max(1, num_samples))

    def clean_frame(self, pcm_bytes: bytes, media_state: MediaState) -> tuple[bytes, bool, float]:
        if self._native is not None:
            res = self._native.process_pcm(pcm_bytes, json.dumps(media_state.to_dict()))
            level = float(res["vad"]["energy_rms"])
            if res["is_gated"]:
                return bytes(len(pcm_bytes)), True, level
            return bytes(res["pcm_clean"]), False, level

        rms = self.compute_rms(pcm_bytes)
        thresh = 0.018 + (media_state.volume_normalized * 0.045 if media_state.is_active else 0.0)
        is_speech = rms >= thresh

        if not is_speech:
            return bytes(len(pcm_bytes)), True, rms

        factor = max(0.15, 1.0 - (media_state.volume_normalized * 0.75)) if media_state.is_active else 1.0
        if abs(factor - 1.0) > 0.01:
            scaled_samples = []
            for i in range(0, len(pcm_bytes) - 1, 2):
                val = int.from_bytes(pcm_bytes[i:i + 2], byteorder="little", signed=True)
                clamped = max(-32768, min(32767, int(val * factor)))
                scaled_samples.append(clamped)
            return b"".join(s.to_bytes(2, byteorder="little", signed=True) for s in scaled_samples), False, rms

        return pcm_bytes, False, rms
