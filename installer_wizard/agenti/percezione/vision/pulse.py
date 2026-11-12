import os

import numpy as np

HEART_BAND = (0.7, 3.5)
BREATH_BAND = (0.1, 0.7)
HEART_RATE = 30.0
BREATH_RATE = 10.0
EPS = 1e-9
FFT_SIZE = 4096
MAX_SAMPLES = 8192


def uniform(ts: np.ndarray, values: np.ndarray, rate: float) -> np.ndarray:
    grid = np.arange(ts[0], ts[-1], 1.0 / rate)
    if values.ndim == 1:
        return np.interp(grid, ts, values)
    return np.stack([np.interp(grid, ts, values[:, i]) for i in range(values.shape[1])], axis=1)


def detrend(signal: np.ndarray) -> np.ndarray:
    x = np.arange(signal.size, dtype=np.float64)
    slope, offset = np.polyfit(x, signal, 1)
    return signal - (slope * x + offset)


def pos(rgb: np.ndarray, rate: float) -> np.ndarray:
    size = rgb.shape[0]
    window = max(2, int(round(1.6 * rate)))
    out = np.zeros(size, dtype=np.float64)
    if size < window:
        return out
    for start in range(size - window + 1):
        chunk = rgb[start:start + window]
        norm = chunk / (chunk.mean(axis=0) + EPS)
        s1 = norm[:, 1] - norm[:, 2]
        s2 = norm[:, 1] + norm[:, 2] - 2.0 * norm[:, 0]
        mixed = s1 + (s1.std() / (s2.std() + EPS)) * s2
        out[start:start + window] += mixed - mixed.mean()
    return out


def dominant(signal: np.ndarray, rate: float, band: tuple[float, float], width: float) -> tuple[float, float]:
    if signal.size < 8 or not np.all(np.isfinite(signal)):
        return 0.0, 0.0
    clean = detrend(signal.astype(np.float64)) * np.hanning(signal.size)
    spectrum = np.abs(np.fft.rfft(clean, n=max(FFT_SIZE, signal.size))) ** 2
    freqs = np.fft.rfftfreq(max(FFT_SIZE, signal.size), 1.0 / rate)
    inside = (freqs >= band[0]) & (freqs <= band[1])
    total = float(spectrum[inside].sum())
    if total <= EPS:
        return 0.0, 0.0
    index = int(np.argmax(np.where(inside, spectrum, 0.0)))
    peak = float(freqs[index])
    if 0 < index < spectrum.size - 1:
        a, b, c = spectrum[index - 1], spectrum[index], spectrum[index + 1]
        denom = a - 2 * b + c
        if abs(denom) > EPS:
            peak += float(0.5 * (a - c) / denom) * float(freqs[1] - freqs[0])
    near = inside & (np.abs(freqs - peak) <= width)
    harmonic = inside & (np.abs(freqs - 2 * peak) <= width)
    quality = float((spectrum[near].sum() + spectrum[harmonic].sum()) / total)
    return peak * 60.0, min(1.0, quality)


def py_heart_rate(ts: np.ndarray, rgb: np.ndarray) -> tuple[float, float]:
    if ts.size < 16 or ts[-1] - ts[0] < 4.0:
        return 0.0, 0.0
    even = uniform(ts, rgb, HEART_RATE)
    if even.shape[0] < 16 or np.any(even.mean(axis=0) <= 1.0):
        return 0.0, 0.0
    return dominant(pos(even, HEART_RATE), HEART_RATE, HEART_BAND, 0.1)


def py_breath_rate(ts: np.ndarray, shift: np.ndarray) -> tuple[float, float]:
    if ts.size < 32 or ts[-1] - ts[0] < 15.0:
        return 0.0, 0.0
    even = np.diff(uniform(ts, shift, BREATH_RATE))
    return dominant(even, BREATH_RATE, BREATH_BAND, 0.04)


def native():
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    return nuxiva_native if hasattr(nuxiva_native, "vitals_heart_rate") else None


_NATIVE = native()


def heart_rate(ts: np.ndarray, rgb: np.ndarray) -> tuple[float, float]:
    if _NATIVE is None or ts.size > MAX_SAMPLES:
        return py_heart_rate(ts, rgb)
    return tuple(_NATIVE.vitals_heart_rate(np.asarray(ts, dtype=np.float64).tolist(), np.asarray(rgb, dtype=np.float64).reshape(-1, 3).tolist()))


def breath_rate(ts: np.ndarray, shift: np.ndarray) -> tuple[float, float]:
    if _NATIVE is None or ts.size > MAX_SAMPLES:
        return py_breath_rate(ts, shift)
    return tuple(_NATIVE.vitals_breath_rate(np.asarray(ts, dtype=np.float64).tolist(), np.asarray(shift, dtype=np.float64).ravel().tolist()))


def py_agreed(seen: list, spread: float) -> int | None:
    if not seen or None in seen or max(seen) - min(seen) > spread:
        return None
    return int(round(float(np.median(seen))))


def agreed(seen: list, window: int, spread: float) -> int | None:
    if len(seen) < window:
        return None
    last = list(seen)[-window:]
    if _NATIVE is None:
        return py_agreed(last, spread)
    return _NATIVE.vitals_agreed([None if v is None else float(v) for v in last], window, float(spread))
