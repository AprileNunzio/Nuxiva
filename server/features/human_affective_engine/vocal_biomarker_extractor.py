from typing import Tuple
import numpy as np
from server.features.human_affective_engine.interfaces import VoiceAcousticBiomarkers

class VocalBiomarkerAnalyzer:
    def __init__(self, sample_rate: int = 16000):
        self._sample_rate = sample_rate

    def extract_biomarkers(self, pcm_signal: np.ndarray) -> VoiceAcousticBiomarkers:
        if len(pcm_signal) == 0:
            return self._default_metrics()

        energy = float(np.sqrt(np.mean(pcm_signal ** 2))) + 1e-9
        pitch_est, pitch_std = self._estimate_pitch_autocorr(pcm_signal)
        monotone = float(np.clip(1.0 - (pitch_std / 35.0), 0.0, 1.0))
        silence_ratio = float(np.mean(np.abs(pcm_signal) < 0.02))

        depressive_score = (
            (monotone * 0.45) +
            (silence_ratio * 0.35) +
            (max(0.0, 1.0 - (energy * 5.0)) * 0.20)
        )

        return VoiceAcousticBiomarkers(
            pitch_f0_mean_hz=pitch_est,
            pitch_variability_st=pitch_std,
            jitter_percent=float(np.clip(pitch_std * 0.08, 0.2, 5.0)),
            shimmer_percent=float(np.clip(silence_ratio * 4.0, 0.5, 12.0)),
            monotone_score=monotone,
            vocal_energy_rms=energy,
            speech_pause_ratio=silence_ratio,
            depressive_vocal_indicator=float(np.clip(depressive_score, 0.0, 1.0))
        )

    def _estimate_pitch_autocorr(self, signal: np.ndarray) -> Tuple[float, float]:
        corr = np.correlate(signal, signal, mode="full")
        corr = corr[len(corr) // 2:]

        min_lag = int(self._sample_rate / 400.0)
        max_lag = int(self._sample_rate / 60.0)

        if max_lag >= len(corr):
            max_lag = len(corr) - 1

        if min_lag >= max_lag:
            return 140.0, 12.0

        peak_lag = min_lag + np.argmax(corr[min_lag:max_lag])
        f0 = float(self._sample_rate / peak_lag) if peak_lag > 0 else 140.0
        frame_size = int(self._sample_rate * 0.05)
        num_frames = max(1, len(signal) // frame_size)
        sub_energies = [float(np.std(signal[i * frame_size : (i + 1) * frame_size])) for i in range(num_frames)]
        energy_dynamics = float(np.std(sub_energies) * 100.0)
        pitch_variability = float(min(45.0, energy_dynamics))
        return float(np.clip(f0, 65.0, 380.0)), pitch_variability

    def _default_metrics(self) -> VoiceAcousticBiomarkers:
        return VoiceAcousticBiomarkers(
            pitch_f0_mean_hz=140.0,
            pitch_variability_st=15.0,
            jitter_percent=0.8,
            shimmer_percent=2.2,
            monotone_score=0.25,
            vocal_energy_rms=0.15,
            speech_pause_ratio=0.15,
            depressive_vocal_indicator=0.15
        )

vocal_biomarker_analyzer = VocalBiomarkerAnalyzer()
