import numpy as np
from scipy.signal import lfilter, oaconvolve

from features.musicstudio.dsp import SR, filt, modulated_delay, shifted

RNG = np.random.default_rng(11)


def _p(params: dict, key: str, default: float) -> float:
    value = params.get(key)
    return float(value) if isinstance(value, (int, float)) and np.isfinite(value) else default


def _mix(dry: np.ndarray, wet: np.ndarray, amount: float) -> np.ndarray:
    m = min(1.0, max(0.0, amount))
    return dry * np.cos(m * np.pi / 2) + wet * np.sin(m * np.pi / 2)


def eq3(x, p, beat):
    out = filt(x, "lowshelf", 220, 0.7, _p(p, "low", 0))
    out = filt(out, "peaking", 1400, 0.8, _p(p, "mid", 0))
    return filt(out, "highshelf", 5200, 0.7, _p(p, "high", 0))


def filter_(x, p, beat):
    kind = ("lowpass", "highpass", "bandpass")[min(2, max(0, int(round(_p(p, "type", 0)))))]
    return filt(x, kind, _p(p, "cutoff", 8000), _p(p, "q", 0.9))


def delay(x, p, beat):
    step = max(1, int(_p(p, "time", 0.375) * beat * SR))
    fb = min(0.92, max(0.0, _p(p, "feedback", 0.35)))
    wet = np.zeros_like(x)
    echo, gain, count = x, 1.0, 0
    while gain > 0.02 and count < 40 and step * (count + 1) < x.shape[-1]:
        echo = shifted(echo, step)
        gain *= fb
        wet += echo * gain
        count += 1
        if fb <= 0.001:
            break
    return x + wet * _p(p, "mix", 0.25)


def reverb(x, p, beat):
    size = min(6.0, max(0.2, _p(p, "size", 2.2)))
    damp = min(1.0, max(0.0, _p(p, "damp", 0.4)))
    n = int(size * SR)
    ir = RNG.standard_normal((2, n)).astype(np.float32) * (1 - np.arange(n) / n) ** 2.4
    ir = filt(ir, "lowpass", 14000 - damp * 11000, 0.5)
    ir /= np.sqrt(np.sum(ir ** 2, axis=-1, keepdims=True)) + 1e-9
    stereo = x if x.ndim == 2 else np.stack([x, x])
    wet = np.stack([oaconvolve(stereo[c], ir[c])[: stereo.shape[-1]] for c in range(2)]).astype(np.float32)
    return _mix(stereo, wet * 0.6, _p(p, "mix", 0.25))


def chorus(x, p, beat):
    wet = modulated_delay(x, 0.022, 0.002 + _p(p, "depth", 0.5) * 0.006, _p(p, "rate", 0.8))
    return _mix(x, wet, _p(p, "mix", 0.4))


def distortion(x, p, beat):
    k = 1 + _p(p, "drive", 0.4) * 60
    wet = np.tanh(k * x) / np.tanh(k)
    wet = filt(wet.astype(np.float32), "lowpass", 600 + _p(p, "tone", 0.6) * 9400, 0.7)
    return _mix(x, wet, _p(p, "mix", 0.5))


def compressor(x, p, beat):
    threshold, ratio = _p(p, "threshold", -18), max(1.0, _p(p, "ratio", 4))
    coefficient = np.exp(-1.0 / (SR * max(0.002, (_p(p, "attack", 0.01) + _p(p, "release", 0.2)) / 2)))
    peak = np.max(np.abs(x), axis=0) if x.ndim == 2 else np.abs(x)
    env = lfilter([1 - coefficient], [1, -coefficient], peak).astype(np.float32)
    over = np.maximum(0.0, 20 * np.log10(env + 1e-9) - threshold)
    gain = 10 ** (-(over * (1 - 1 / ratio)) / 20)
    return x * gain.astype(np.float32) * 10 ** (min(12.0, abs(threshold) * (1 - 1 / ratio) * 0.25) / 20)


def tremolo(x, p, beat):
    depth = min(1.0, max(0.0, _p(p, "depth", 0.5)))
    t = np.arange(x.shape[-1]) / SR
    return x * (1 - depth * 0.5 + depth * 0.5 * np.sin(2 * np.pi * _p(p, "rate", 5) * t)).astype(np.float32)


def flanger(x, p, beat):
    depth = _p(p, "depth", 0.6)
    wet = modulated_delay(x, 0.004, 0.0005 + depth * 0.003, _p(p, "rate", 0.3))
    wet = wet + modulated_delay(wet, 0.004, 0.0005 + depth * 0.003, _p(p, "rate", 0.3)) * _p(p, "feedback", 0.4)
    return _mix(x, wet, _p(p, "mix", 0.5))


def bitcrusher(x, p, beat):
    steps = 2.0 ** min(16.0, max(2.0, _p(p, "bits", 8)))
    hold = max(1, int(round(1 / max(0.05, _p(p, "rate", 0.5)))))
    wet = np.round(x * steps * 0.5) / (steps * 0.5)
    if hold > 1:
        n = wet.shape[-1]
        wet = np.repeat(wet[..., ::hold], hold, axis=-1)[..., :n]
    return _mix(x, wet.astype(np.float32), _p(p, "mix", 0.6))


def autopan(x, p, beat):
    stereo = x if x.ndim == 2 else np.stack([x, x])
    t = np.arange(stereo.shape[-1]) / SR
    angle = (np.sin(2 * np.pi * _p(p, "rate", 1) * t) * min(1.0, max(0.0, _p(p, "depth", 0.7))) + 1) * np.pi / 4
    return np.stack([stereo[0] * np.cos(angle) * 1.414, stereo[1] * np.sin(angle) * 1.414]).astype(np.float32)


def limiter(x, p, beat):
    ceiling = 10 ** (min(0.0, _p(p, "ceiling", -1)) / 20)
    return (ceiling * np.tanh(x / ceiling)).astype(np.float32)


def phaser(x, p, beat):
    depth, rate = _p(p, "depth", 0.6), _p(p, "rate", 0.5)
    block = 1024
    wet = x.copy()
    for stage in range(4):
        zi = np.zeros(x.shape[:-1] + (1,), dtype=np.float64)
        for start in range(0, x.shape[-1], block):
            lfo = np.sin(2 * np.pi * rate * (start / SR) + stage * 0.4)
            freq = 800 * (1 + (0.5 + 0.5 * depth) * lfo * 0.9)
            tan = np.tan(np.pi * min(freq, SR * 0.4) / SR)
            c = (tan - 1) / (tan + 1)
            part, zi = lfilter([c, 1.0], [1.0, c], wet[..., start: start + block], axis=-1, zi=zi)
            wet[..., start: start + block] = part
    return _mix(x, wet, _p(p, "mix", 0.5))


APPLY = {"eq3": eq3, "filter": filter_, "delay": delay, "reverb": reverb, "chorus": chorus, "distortion": distortion, "compressor": compressor, "tremolo": tremolo,
         "flanger": flanger, "bitcrusher": bitcrusher, "autopan": autopan, "limiter": limiter, "phaser": phaser}


def chain(x: np.ndarray, effects: list, beat: float) -> np.ndarray:
    for effect in effects:
        fn = APPLY.get(effect.get("type"))
        if fn and effect.get("on", True):
            x = fn(x, effect.get("params") or {}, beat).astype(np.float32)
    return x
