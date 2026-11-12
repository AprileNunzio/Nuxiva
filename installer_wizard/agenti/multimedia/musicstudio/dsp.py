import numpy as np
from scipy.signal import lfilter

SR = 44100


def hz(midi: float) -> float:
    return 440.0 * 2.0 ** ((midi - 69.0) / 12.0)


def biquad(kind: str, freq: float, q: float = 0.7, gain: float = 0.0, sr: int = SR):
    freq = float(min(max(freq, 20.0), sr * 0.45))
    w = 2 * np.pi * freq / sr
    cos, sin = np.cos(w), np.sin(w)
    alpha = sin / (2 * max(q, 0.05))
    a_gain = 10 ** (gain / 40)
    if kind == "lowpass":
        b = [(1 - cos) / 2, 1 - cos, (1 - cos) / 2]
        a = [1 + alpha, -2 * cos, 1 - alpha]
    elif kind == "highpass":
        b = [(1 + cos) / 2, -(1 + cos), (1 + cos) / 2]
        a = [1 + alpha, -2 * cos, 1 - alpha]
    elif kind == "bandpass":
        b = [alpha, 0.0, -alpha]
        a = [1 + alpha, -2 * cos, 1 - alpha]
    elif kind == "peaking":
        b = [1 + alpha * a_gain, -2 * cos, 1 - alpha * a_gain]
        a = [1 + alpha / a_gain, -2 * cos, 1 - alpha / a_gain]
    else:
        root = 2 * np.sqrt(a_gain) * alpha
        sign = 1 if kind == "lowshelf" else -1
        b = [a_gain * ((a_gain + 1) - sign * (a_gain - 1) * cos + root), sign * 2 * a_gain * ((a_gain - 1) - sign * (a_gain + 1) * cos),
             a_gain * ((a_gain + 1) - sign * (a_gain - 1) * cos - root)]
        a = [(a_gain + 1) + sign * (a_gain - 1) * cos + root, -sign * 2 * ((a_gain - 1) + sign * (a_gain + 1) * cos), (a_gain + 1) + sign * (a_gain - 1) * cos - root]
    b = np.asarray(b, dtype=np.float64)
    a = np.asarray(a, dtype=np.float64)
    return b / a[0], a / a[0]


def filt(x: np.ndarray, kind: str, freq: float, q: float = 0.7, gain: float = 0.0) -> np.ndarray:
    b, a = biquad(kind, freq, q, gain)
    return lfilter(b, a, x, axis=-1).astype(np.float32)


def shifted(x: np.ndarray, delay: int) -> np.ndarray:
    out = np.zeros_like(x)
    if 0 < delay < x.shape[-1]:
        out[..., delay:] = x[..., : x.shape[-1] - delay]
    elif delay <= 0:
        out = x.copy()
    return out


def modulated_delay(x: np.ndarray, base: float, depth: float, rate: float) -> np.ndarray:
    n = x.shape[-1]
    t = np.arange(n, dtype=np.float64)
    delay = base * SR + depth * SR * np.sin(2 * np.pi * rate * t / SR)
    pos = np.clip(t - delay, 0, n - 1)
    lo = np.floor(pos).astype(np.int64)
    hi = np.minimum(lo + 1, n - 1)
    frac = (pos - lo).astype(np.float32)
    return x[..., lo] * (1 - frac) + x[..., hi] * frac
