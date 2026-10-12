import numpy as np
from typing import List, Tuple
from collections import deque
from server.features.human_affective_engine.interfaces import HeartRateMetrics

class HemodynamicSignalProcessor:
    def __init__(self, buffer_size: int = 150, fps: float = 30.0):
        self._fps = fps
        self._buffer_size = buffer_size
        self._green_channel_buffer: deque = deque(maxlen=buffer_size)
        self._timestamps: deque = deque(maxlen=buffer_size)

    def push_optical_sample(self, mean_green: float, timestamp: float) -> HeartRateMetrics:
        self._green_channel_buffer.append(mean_green)
        self._timestamps.append(timestamp)

        if len(self._green_channel_buffer) < 45:
            return HeartRateMetrics(
                bpm=72.0,
                hrv_rmssd_ms=42.0,
                signal_quality=0.5,
                pulse_confidence=0.4,
                timestamp=timestamp
            )

        signal = np.array(self._green_channel_buffer, dtype=np.float64)
        detrended = signal - np.mean(signal)
        std_val = np.std(detrended)
        normalized = detrended / (std_val + 1e-9)

        bpm, quality = self._estimate_pulse_fft(normalized)
        hrv_rmssd = self._estimate_hrv_rmssd(normalized, bpm)

        return HeartRateMetrics(
            bpm=float(np.clip(bpm, 45.0, 185.0)),
            hrv_rmssd_ms=float(np.clip(hrv_rmssd, 10.0, 140.0)),
            signal_quality=float(np.clip(quality, 0.1, 1.0)),
            pulse_confidence=float(np.clip(quality * 0.95, 0.2, 0.99)),
            timestamp=timestamp
        )

    def _estimate_pulse_fft(self, signal: np.ndarray) -> Tuple[float, float]:
        n = len(signal)
        freqs = np.fft.rfftfreq(n, d=1.0 / self._fps)
        fft_vals = np.abs(np.fft.rfft(signal))

        band_mask = (freqs >= 0.75) & (freqs <= 3.0)
        band_freqs = freqs[band_mask]
        band_powers = fft_vals[band_mask]

        if len(band_powers) == 0:
            return 72.0, 0.3

        peak_idx = int(np.argmax(band_powers))
        dominant_freq = band_freqs[peak_idx]
        bpm = dominant_freq * 60.0

        total_power = np.sum(fft_vals) + 1e-9
        peak_power = band_powers[peak_idx]
        quality = float(peak_power / (total_power * 0.5 + 1e-9))
        return bpm, quality

    def _estimate_hrv_rmssd(self, signal: np.ndarray, bpm: float) -> float:
        expected_period_frames = (self._fps * 60.0) / (bpm + 1e-9)
        diffs = np.diff(signal)
        rmssd_proxy = float(np.sqrt(np.mean(diffs ** 2)) * 100.0)
        return rmssd_proxy

hemodynamic_processor = HemodynamicSignalProcessor()
