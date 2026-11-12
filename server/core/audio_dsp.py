import json
import math
from typing import Any, Dict, List, Optional


class MediaPlaybackState:
    def __init__(
        self,
        is_active: bool = False,
        source_id: str = "",
        stream_type: str = "NONE",
        volume_normalized: float = 0.0,
        reference_energy: float = 0.0,
    ) -> None:
        self.is_active = is_active
        self.source_id = source_id
        self.stream_type = stream_type
        self.volume_normalized = max(0.0, min(1.0, float(volume_normalized)))
        self.reference_energy = max(0.0, float(reference_energy))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_active": self.is_active,
            "source_id": self.source_id,
            "stream_type": self.stream_type,
            "volume_normalized": self.volume_normalized,
            "reference_energy": self.reference_energy,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MediaPlaybackState":
        return cls(
            is_active=bool(data.get("is_active", False)),
            source_id=str(data.get("source_id", "")),
            stream_type=str(data.get("stream_type", "NONE")),
            volume_normalized=float(data.get("volume_normalized", 0.0)),
            reference_energy=float(data.get("reference_energy", 0.0)),
        )


class AudioDevice:
    def __init__(
        self,
        id: str,
        name_key: str,
        priority: int,
        is_connected: bool = True,
        is_bluetooth: bool = False,
        battery_level: Optional[int] = None,
    ) -> None:
        self.id = id
        self.name_key = name_key
        self.priority = int(priority)
        self.is_connected = is_connected
        self.is_bluetooth = is_bluetooth
        self.battery_level = battery_level

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name_key": self.name_key,
            "priority": self.priority,
            "is_connected": self.is_connected,
            "is_bluetooth": self.is_bluetooth,
            "battery_level": self.battery_level,
        }


class SatelliteAudioReport:
    def __init__(
        self,
        satellite_id: str,
        timestamp_ms: int,
        snr_db: float,
        energy_rms: float,
        speech_confidence: float,
    ) -> None:
        self.satellite_id = satellite_id
        self.timestamp_ms = int(timestamp_ms)
        self.snr_db = float(snr_db)
        self.energy_rms = float(energy_rms)
        self.speech_confidence = float(speech_confidence)

    def proximity_score(self) -> float:
        snr_part = max(0.0, min(50.0, self.snr_db)) * 0.45
        energy_part = max(0.0, min(50.0, self.energy_rms * 100.0)) * 0.35
        conf_part = max(0.0, min(1.0, self.speech_confidence)) * 20.0
        return snr_part + energy_part + conf_part

    def to_dict(self) -> Dict[str, Any]:
        return {
            "satellite_id": self.satellite_id,
            "timestamp_ms": self.timestamp_ms,
            "snr_db": self.snr_db,
            "energy_rms": self.energy_rms,
            "speech_confidence": self.speech_confidence,
        }


class AudioCleanerBridge:
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

    def process_pcm(self, pcm_bytes: bytes, media_state: MediaPlaybackState) -> Dict[str, Any]:
        if self._native is not None:
            return self._native.process_pcm(pcm_bytes, json.dumps(media_state.to_dict()))

        rms = self.compute_rms(pcm_bytes)
        base_thresh = 0.018 + (media_state.volume_normalized * 0.045 if media_state.is_active else 0.0)
        is_speech = rms >= base_thresh

        decision = "SPEECH" if is_speech else ("MUSIC_OR_BACKGROUND" if media_state.is_active and rms > 0.01 else "SILENCE")
        factor = max(0.15, 1.0 - (media_state.volume_normalized * 0.75)) if media_state.is_active else 1.0

        usable = len(pcm_bytes) - (len(pcm_bytes) % 2)
        clean_bytes = pcm_bytes[:usable] if is_speech else bytes(usable)
        num_samples = usable // 2

        return {
            "pcm_clean": clean_bytes,
            "vad": {
                "decision": decision,
                "speech_confidence": 0.85 if is_speech else 0.1,
                "energy_rms": rms,
                "is_speech": is_speech,
                "reason_code": "vad_speech_detected" if is_speech else "vad_silence",
            },
            "is_gated": not is_speech,
            "attenuation_applied": 0.0 if not is_speech else factor,
            "frame_samples": num_samples,
        }

    def reset(self) -> None:
        if self._native is not None:
            self._native.reset()


class FailoverDeviceRouterBridge:
    def __init__(self, is_proximity: bool = False) -> None:
        self._devices: List[AudioDevice] = []
        self._is_proximity = is_proximity
        self._native = None
        try:
            import nuxiva_native
            if hasattr(nuxiva_native, "RustDeviceRouter"):
                self._native = nuxiva_native.RustDeviceRouter(is_proximity)
        except ImportError:
            self._native = None

    def register_device(self, device: AudioDevice) -> None:
        self._devices = [d for d in self._devices if d.id != device.id]
        self._devices.append(device)
        self._devices.sort(key=lambda d: d.priority)
        if self._native is not None:
            self._native.register_device_json(json.dumps(device.to_dict()))

    def update_connection_state(self, device_id: str, is_connected: bool) -> None:
        for dev in self._devices:
            if dev.id == device_id:
                dev.is_connected = is_connected
        if self._native is not None:
            self._native.update_connection_state(device_id, is_connected)

    def resolve_active_device(self) -> Optional[AudioDevice]:
        if self._native is not None:
            raw = self._native.resolve_active_device_json()
            if raw:
                data = json.loads(raw)
                return AudioDevice(
                    id=data["id"],
                    name_key=data["name_key"],
                    priority=data["priority"],
                    is_connected=data["is_connected"],
                    is_bluetooth=data["is_bluetooth"],
                    battery_level=data.get("battery_level"),
                )
            return None

        for dev in self._devices:
            if dev.is_connected:
                return dev
        return None


class MultiMicTriageBridge:
    def __init__(self, hysteresis_margin: float = 3.5) -> None:
        self.hysteresis_margin = float(hysteresis_margin)
        self._active_winner_id: Optional[str] = None
        self._last_winning_score: float = 0.0
        self._native = None
        try:
            import nuxiva_native
            if hasattr(nuxiva_native, "RustMultiMicTriage"):
                self._native = nuxiva_native.RustMultiMicTriage(self.hysteresis_margin)
        except ImportError:
            self._native = None

    def elect_best_source(self, reports: List[SatelliteAudioReport]) -> Optional[str]:
        if self._native is not None:
            reports_json = json.dumps([r.to_dict() for r in reports])
            return self._native.elect_best_source_json(reports_json)

        if not reports:
            return self._active_winner_id

        best_id: Optional[str] = None
        best_score = -1.0
        for report in reports:
            score = report.proximity_score()
            if score > best_score:
                best_score = score
                best_id = report.satellite_id

        if self._active_winner_id is not None and best_id is not None:
            if best_id != self._active_winner_id:
                if best_score > (self._last_winning_score + self.hysteresis_margin):
                    self._active_winner_id = best_id
                    self._last_winning_score = best_score
            else:
                self._last_winning_score = best_score
        elif best_id is not None:
            self._active_winner_id = best_id
            self._last_winning_score = best_score

        return self._active_winner_id

    def reset(self) -> None:
        self._active_winner_id = None
        self._last_winning_score = 0.0
        if self._native is not None:
            self._native.reset()
