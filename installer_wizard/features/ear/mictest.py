import io
import math
import wave
from dataclasses import dataclass

import numpy as np

from features.ear import equalizer
from features.ear.levels import CLIP, LOUD, QUIET, GainFollower, judge, utterance_gain, voice_floor, voiced_rms

RATE = 16000
FRAME = 480
METER_FRAME = 800
FLOOR_DB = -90.0
SILENT_RMS = 0.002
NOISE_PERCENTILE = 20
LIMITER_PEAK = 0.97


@dataclass(frozen=True, slots=True)
class Chain:
    eq: equalizer.EqSettings
    target_rms: float
    max_gain: float
    wake_gain_limit: float
    autotuned: bool


def to_samples(pcm: bytes) -> np.ndarray:
    if len(pcm) % 2:
        pcm = pcm[:-1]
    return np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0


def dbfs(value: float) -> float:
    return round(max(FLOOR_DB, 20.0 * math.log10(value)) if value > 0 else FLOOR_DB, 1)


def zone(rms: float, peak: float) -> str:
    if peak >= CLIP:
        return "clip"
    if rms >= LOUD:
        return "loud"
    if rms < SILENT_RMS:
        return "silent"
    if rms < QUIET:
        return "quiet"
    return "good"


def meter(samples: np.ndarray) -> dict:
    rms = float(np.sqrt(np.mean(samples * samples))) if samples.size else 0.0
    peak = float(np.abs(samples).max()) if samples.size else 0.0
    return {"rms": round(rms, 5), "peak": round(peak, 5), "rms_db": dbfs(rms), "peak_db": dbfs(peak), "zone": zone(rms, peak)}


def frames_of(samples: np.ndarray, size: int) -> np.ndarray:
    count = len(samples) // size
    return samples[:count * size].reshape(count, size) if count else np.zeros((0, size), dtype=np.float32)


def timeline(samples: np.ndarray) -> list[dict]:
    return [meter(frame) for frame in frames_of(samples, METER_FRAME)]


def wake_gain(frames: np.ndarray, rms: np.ndarray, noise: float, limit: float) -> tuple[float, float]:
    follower = GainFollower()
    gains = []
    for frame, level in zip(frames, rms):
        _, voiced = follower.follow(frame, float(level), noise, limit)
        if voiced:
            gains.append(follower.gain)
    final = follower.gain
    return round(final, 2), round(float(np.median(gains)) if gains else final, 2)


def levels_report(samples: np.ndarray, limit: float) -> dict:
    frames = frames_of(samples, FRAME)
    if not len(frames):
        return {"verdict": "silent", "voiced_ratio": 0.0}
    rms = np.sqrt((frames * frames).mean(axis=1))
    peaks = np.abs(frames).max(axis=1)
    noise = float(np.percentile(rms, NOISE_PERCENTILE))
    voiced = rms > voice_floor(noise)
    voiced_peak_rms = float(rms[voiced].max()) if voiced.any() else 0.0
    clip_ratio = float((peaks[voiced] >= CLIP).mean()) if voiced.any() else 0.0
    verdict = judge(voiced_peak_rms, clip_ratio) if voiced.any() and voiced_peak_rms >= SILENT_RMS else "silent"
    final_gain, median_gain = wake_gain(frames, rms, noise, limit)
    voice = float(rms[voiced].mean()) if voiced.any() else 0.0
    return {"verdict": verdict, "peak_db": dbfs(float(peaks.max())), "voice_db": dbfs(voice), "noise_db": dbfs(noise),
            "snr_db": round(dbfs(voice) - dbfs(noise), 1) if voiced.any() else 0.0,
            "clip_ratio": round(clip_ratio, 4), "voiced_ratio": round(float(voiced.mean()), 3),
            "wake_gain": final_gain, "wake_gain_median": median_gain}


def process(samples: np.ndarray, chain: Chain) -> tuple[np.ndarray, float]:
    shaped = equalizer.apply(samples, chain.eq)
    gain = utterance_gain(shaped, chain.target_rms, chain.max_gain)
    out = LIMITER_PEAK * np.tanh(shaped * gain / LIMITER_PEAK)
    return out.astype(np.float32), gain


def wav_bytes(samples: np.ndarray) -> bytes:
    pcm = np.round(np.clip(samples, -1.0, 32767 / 32768) * 32768.0).astype("<i2").tobytes()
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(pcm)
    return buffer.getvalue()


def analyze(pcm: bytes, chain: Chain) -> tuple[dict, bytes, bytes]:
    samples = to_samples(pcm)
    processed, gain = process(samples, chain)
    report = {
        "seconds": round(len(samples) / RATE, 2),
        **levels_report(samples, chain.wake_gain_limit),
        "phrase_gain": round(gain, 2),
        "phrase_voice_db": dbfs(voiced_rms(processed)),
        "limits": {"wake_gain": round(chain.wake_gain_limit, 2), "max_gain": round(chain.max_gain, 1),
                   "target_rms": round(chain.target_rms, 3), "autotuned": chain.autotuned},
        "eq": chain.eq.as_dict(),
        "timeline": timeline(samples),
    }
    return report, wav_bytes(samples), wav_bytes(processed)
