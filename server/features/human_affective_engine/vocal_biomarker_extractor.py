from typing import Any, Dict, Tuple
import numpy as np
from server.features.human_affective_engine.interfaces import (
    VocalDeliveryMode,
    VoiceAcousticBiomarkers,
)

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None


def _native_analyzer(sample_rate: int) -> Any:
    if nuxiva_native is None or not hasattr(nuxiva_native, "RustVoiceBiomarkers"):
        return None
    return nuxiva_native.RustVoiceBiomarkers(sample_rate)


class VocalBiomarkerAnalyzer:
    def __init__(self, sample_rate: int = 16000):
        self._sample_rate = sample_rate
        self._native = _native_analyzer(sample_rate)

    def extract_from_pcm16_bytes(self, pcm_bytes: bytes) -> VoiceAcousticBiomarkers:
        if not pcm_bytes:
            return self._default_metrics()
        samples = np.frombuffer(pcm_bytes, dtype="<i2").astype(np.float32) / 32768.0
        return self.extract_biomarkers(samples)

    def extract_biomarkers(self, pcm_signal: np.ndarray) -> VoiceAcousticBiomarkers:
        signal = np.asarray(pcm_signal, dtype=np.float32).reshape(-1)
        if len(signal) == 0:
            return self._default_metrics()

        base_fields: Dict[str, Any]
        if self._native is not None:
            samples = np.ascontiguousarray(signal, dtype="<f4").tobytes()
            base_fields = dict(self._native.extract_f32(samples))
        else:
            energy = float(np.sqrt(np.mean(signal ** 2))) + 1e-9
            pitch_est, pitch_std, _ = self._estimate_pitch_and_voicing(signal)
            monotone = float(np.clip(1.0 - (pitch_std / 35.0), 0.0, 1.0))
            silence_ratio = float(np.mean(np.abs(signal) < 0.02))

            depressive_score = (
                (monotone * 0.45) +
                (silence_ratio * 0.35) +
                (max(0.0, 1.0 - (energy * 5.0)) * 0.20)
            )
            base_fields = {
                "pitch_f0_mean_hz": pitch_est,
                "pitch_variability_st": pitch_std,
                "jitter_percent": float(np.clip(pitch_std * 0.08, 0.2, 5.0)),
                "shimmer_percent": float(np.clip(silence_ratio * 4.0, 0.5, 12.0)),
                "monotone_score": monotone,
                "vocal_energy_rms": energy,
                "speech_pause_ratio": silence_ratio,
                "depressive_vocal_indicator": float(np.clip(depressive_score, 0.0, 1.0)),
            }

        paraling = self._extract_paralinguistic_features(signal, base_fields)
        base_fields.update(paraling)
        return VoiceAcousticBiomarkers(**base_fields)

    def _extract_paralinguistic_features(
        self,
        signal: np.ndarray,
        base_fields: Dict[str, Any],
    ) -> Dict[str, Any]:
        centered = signal - float(np.mean(signal))
        energy_rms = float(base_fields["vocal_energy_rms"])
        _, _, voicing_strength = self._estimate_pitch_and_voicing(centered)

        # Harmonic-to-Noise Ratio (dB) derived from normalized autocorrelation peak
        r = float(np.clip(voicing_strength, 1e-4, 0.999))
        hnr_db = float(np.clip(10.0 * np.log10(r / (1.0 - r)), -20.0, 35.0))

        # Zero-crossing rate (turbulent unvoiced airflow / whisper has higher ZCR)
        if len(centered) > 1:
            signs = np.signbit(centered)
            zcr = float(np.mean(signs[1:] != signs[:-1]))
        else:
            zcr = 0.0

        # Spectral tilt: ratio of high-frequency turbulence (1.5-6 kHz) vs speech band (80-6000 Hz)
        hf_ratio = self._compute_high_freq_energy_ratio(centered)

        # Estimated syllable speech rate from smoothed amplitude envelope
        speech_rate_sps = self._estimate_speech_rate_sps(centered)

        # Whisper detection:
        # True whisper is active (not silence), low-to-moderate RMS, unvoiced (low voicing/HNR),
        # spectrally tilted toward high frequencies, with elevated zero-crossing rate.
        is_audible = energy_rms >= 0.0025 and float(np.std(centered)) > 1e-4
        if not is_audible:
            whisper_prob = 0.0
        else:
            low_energy_score = float(np.clip((0.12 - energy_rms) / 0.10, 0.0, 1.0))
            unvoiced_score = float(np.clip((0.45 - voicing_strength) / 0.35, 0.0, 1.0))
            hf_score = float(np.clip((hf_ratio - 0.30) / 0.45, 0.0, 1.0))
            zcr_score = float(np.clip((zcr - 0.10) / 0.25, 0.0, 1.0))
            whisper_prob = float(np.clip(
                (unvoiced_score * 0.40)
                + (hf_score * 0.25)
                + (low_energy_score * 0.20)
                + (zcr_score * 0.15),
                0.0,
                1.0,
            ))

        delivery_mode = self._classify_delivery_mode(
            energy_rms=energy_rms,
            whisper_prob=whisper_prob,
            voicing_strength=voicing_strength,
            pitch_var=float(base_fields["pitch_variability_st"]),
            monotone=float(base_fields["monotone_score"]),
            pause_ratio=float(base_fields["speech_pause_ratio"]),
            jitter=float(base_fields["jitter_percent"]),
            speech_rate_sps=speech_rate_sps,
        )

        return {
            "whisper_probability": whisper_prob,
            "harmonic_to_noise_ratio_db": hnr_db,
            "high_freq_energy_ratio": hf_ratio,
            "zero_crossing_rate": zcr,
            "speech_rate_sps": speech_rate_sps,
            "voicing_strength": voicing_strength,
            "delivery_mode": delivery_mode,
        }

    def _compute_high_freq_energy_ratio(self, centered: np.ndarray) -> float:
        if len(centered) < 64 or float(np.std(centered)) < 1e-6:
            return 0.0
        window = np.hanning(len(centered))
        spectrum = np.abs(np.fft.rfft(centered * window)) ** 2
        freqs = np.fft.rfftfreq(len(centered), d=1.0 / self._sample_rate)

        speech_band = (freqs >= 80.0) & (freqs <= 6000.0)
        high_band = (freqs >= 1500.0) & (freqs <= 6000.0)

        total_power = float(np.sum(spectrum[speech_band]))
        if total_power <= 1e-12:
            return 0.0
        high_power = float(np.sum(spectrum[high_band]))
        return float(np.clip(high_power / total_power, 0.0, 1.0))

    def _estimate_speech_rate_sps(self, centered: np.ndarray) -> float:
        duration_s = len(centered) / float(self._sample_rate)
        if duration_s < 0.2 or float(np.std(centered)) < 1e-5:
            return 0.0

        # Smooth amplitude envelope with ~40ms window
        win = max(1, int(self._sample_rate * 0.04))
        env = np.convolve(np.abs(centered), np.ones(win, dtype=np.float32) / win, mode="same")
        # Downsample envelope to ~100 Hz for fast peak counting
        step = max(1, self._sample_rate // 100)
        env_ds = env[::step]
        if len(env_ds) < 5:
            return 0.0

        threshold = max(float(np.mean(env_ds)) * 1.15, 0.005)
        min_gap_frames = 12  # ~120ms minimum gap between syllable nuclei
        peaks = 0
        last_peak = -min_gap_frames
        for i in range(1, len(env_ds) - 1):
            if (
                env_ds[i] > threshold
                and env_ds[i] >= env_ds[i - 1]
                and env_ds[i] > env_ds[i + 1]
                and (i - last_peak) >= min_gap_frames
            ):
                peaks += 1
                last_peak = i

        return float(np.clip(peaks / duration_s, 0.0, 12.0))

    def _classify_delivery_mode(
        self,
        *,
        energy_rms: float,
        whisper_prob: float,
        voicing_strength: float,
        pitch_var: float,
        monotone: float,
        pause_ratio: float,
        jitter: float,
        speech_rate_sps: float,
    ) -> VocalDeliveryMode:
        if whisper_prob >= 0.60:
            return VocalDeliveryMode.WHISPER
        if energy_rms >= 0.35 and (pitch_var >= 20.0 or jitter >= 2.0):
            return VocalDeliveryMode.SHOUTING
        if (pitch_var >= 28.0 or jitter >= 2.5) and speech_rate_sps >= 4.2:
            return VocalDeliveryMode.TENSE_URGENT
        if energy_rms >= 0.16 and pitch_var >= 18.0 and monotone < 0.45:
            return VocalDeliveryMode.ANIMATED_EXCITED
        if energy_rms < 0.07 and voicing_strength >= 0.45 and pause_ratio < 0.55:
            return VocalDeliveryMode.SOFT_INTIMATE
        if pause_ratio >= 0.50 and speech_rate_sps <= 2.5:
            return VocalDeliveryMode.FATIGUED_SLOW
        if monotone >= 0.75:
            return VocalDeliveryMode.FLAT_MONOTONE
        return VocalDeliveryMode.CALM_NATURAL

    def _estimate_pitch_and_voicing(self, signal: np.ndarray) -> Tuple[float, float, float]:
        centered = signal - float(np.mean(signal))
        zero_lag = float(np.dot(centered, centered))
        if zero_lag <= 1e-10:
            return 140.0, 0.0, 0.0

        # FFT-based autocorrelation for O(N log N) speed on real audio chunks
        n = len(centered)
        fft_size = 1 << (2 * n - 1).bit_length()
        spec = np.fft.rfft(centered, n=fft_size)
        corr = np.fft.irfft(spec * np.conj(spec), n=fft_size)[:n]

        min_lag = int(self._sample_rate / 400.0)
        max_lag = int(self._sample_rate / 60.0)

        if max_lag >= len(corr):
            max_lag = len(corr) - 1

        if min_lag >= max_lag:
            return 140.0, 12.0, 0.0

        search_slice = corr[min_lag:max_lag]
        peak_offset = int(np.argmax(search_slice))
        peak_lag = min_lag + peak_offset
        voicing_strength = float(np.clip(search_slice[peak_offset] / zero_lag, 0.0, 1.0))

        f0 = float(self._sample_rate / peak_lag) if peak_lag > 0 else 140.0
        frame_size = max(1, int(self._sample_rate * 0.05))
        num_frames = max(1, len(signal) // frame_size)
        sub_energies = [
            float(np.std(signal[i * frame_size : (i + 1) * frame_size]))
            for i in range(num_frames)
        ]
        energy_dynamics = float(np.std(sub_energies) * 100.0)
        pitch_variability = float(min(45.0, energy_dynamics))
        return float(np.clip(f0, 65.0, 380.0)), pitch_variability, voicing_strength

    def _default_metrics(self) -> VoiceAcousticBiomarkers:
        return VoiceAcousticBiomarkers(
            pitch_f0_mean_hz=140.0,
            pitch_variability_st=15.0,
            jitter_percent=0.8,
            shimmer_percent=2.2,
            monotone_score=0.25,
            vocal_energy_rms=0.15,
            speech_pause_ratio=0.15,
            depressive_vocal_indicator=0.15,
            whisper_probability=0.0,
            harmonic_to_noise_ratio_db=12.0,
            high_freq_energy_ratio=0.25,
            zero_crossing_rate=0.08,
            speech_rate_sps=3.5,
            voicing_strength=0.7,
            delivery_mode=VocalDeliveryMode.CALM_NATURAL,
        )

vocal_biomarker_analyzer = VocalBiomarkerAnalyzer()
