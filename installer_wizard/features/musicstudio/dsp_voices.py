import numpy as np

from features.musicstudio.dsp import SR, filt, hz

RNG = np.random.default_rng(7)


def _num(value, fallback: float) -> float:
    return float(value) if isinstance(value, (int, float)) and np.isfinite(value) else fallback


def _wave(kind: str, phase: np.ndarray) -> np.ndarray:
    if kind == "sine":
        return np.sin(2 * np.pi * phase)
    if kind == "triangle":
        return 2 * np.abs(2 * (phase % 1.0) - 1) - 1
    if kind == "square":
        return np.sign(np.sin(2 * np.pi * phase)) * 0.8
    return (2 * (phase % 1.0) - 1) * 0.8


def _envelope(n: int, hold: int, a: float, d: float, s: float, r: float) -> np.ndarray:
    env = np.zeros(n, dtype=np.float32)
    na, nd, nr = max(1, int(a * SR)), max(1, int(d * SR)), max(1, int(r * SR))
    head = min(hold, n)
    t = np.arange(head)
    attack = np.minimum(t / na, 1.0)
    decay = np.where(t >= na, np.maximum(s, 1.0 - (1.0 - s) * (t - na) / nd), 1.0)
    env[:head] = attack * np.where(t >= na, decay, 1.0)
    level = env[head - 1] if head else 0.0
    tail = n - head
    if tail > 0:
        env[head:] = level * np.maximum(0.0, 1.0 - np.arange(tail) / nr)
    return env


def synth(voice: dict, midi: int, dur: float, vel: float) -> np.ndarray:
    env = voice.get("env") or {}
    a, d = max(0.001, _num(env.get("a"), 0.01)), max(0.01, _num(env.get("d"), 0.2))
    s, r = min(1.0, max(0.0, _num(env.get("s"), 0.6))), max(0.02, _num(env.get("r"), 0.2))
    hold = max(a + 0.01, dur)
    n = int((hold + r) * SR)
    t = np.arange(n, dtype=np.float64) / SR
    vibrato = voice.get("vibrato") or {}
    cents = _num(vibrato.get("cents"), 0.0)
    wobble = np.zeros(n)
    if cents > 0:
        ramp = np.clip((t - _num(vibrato.get("delay"), 0.15)) / 0.3, 0, 1)
        wobble = cents * ramp * np.sin(2 * np.pi * _num(vibrato.get("rate"), 5.0) * t)
    oscs = [o for o in (voice.get("oscs") or []) if isinstance(o, dict)][:6] or [{"type": "sawtooth", "gain": 1.0}]
    out = np.zeros(n, dtype=np.float64)
    for o in oscs:
        freq = hz(midi + 12 * _num(o.get("octave"), 0.0)) * 2.0 ** ((_num(o.get("detune"), 0.0) + wobble) / 1200.0)
        out += _wave(str(o.get("type", "sawtooth")), np.cumsum(freq) / SR) * min(1.5, max(0.0, _num(o.get("gain"), 1.0)))
    out /= max(1.0, len(oscs) * 0.7)
    breath = _num(voice.get("breath"), 0.0)
    if breath > 0:
        out += filt(RNG.standard_normal(n).astype(np.float32), "bandpass", min(hz(midi) * 3, 6000), 0.8) * breath * 0.6
    flt = voice.get("filter") or {}
    cutoff = _num(flt.get("cutoff"), 8000.0) + 0.3 * _num(flt.get("env"), 0.0)
    out = filt(out.astype(np.float32), "lowpass", min(cutoff, SR * 0.4), _num(flt.get("q"), 0.7))
    return out * _envelope(n, int(hold * SR), a, d, s, r) * (min(1.0, max(0.02, vel)) * 0.32)


def _noise(n: int) -> np.ndarray:
    return RNG.standard_normal(n).astype(np.float32)


def _decay(n: int, time: float, power: float = 5.0) -> np.ndarray:
    return np.exp(-np.arange(n) / (SR * max(time, 0.005) / power)).astype(np.float32)


def _sweep(n: int, start: float, end: float, time: float, kind: str = "sine") -> np.ndarray:
    t = np.arange(n) / SR
    freq = end + (start - end) * np.exp(-t / max(time * 0.25, 0.005))
    phase = np.cumsum(freq) / SR
    return _wave(kind, phase).astype(np.float32)


def drum(voice: dict, lane: str, vel: float) -> np.ndarray:
    level = min(1.0, max(0.05, vel))
    body, snare, hat = _num(voice.get("kick"), 52.0), _num(voice.get("snare"), 190.0), _num(voice.get("hat"), 7600.0)
    punch, snap, tone = _num(voice.get("punch"), 0.8), _num(voice.get("snap"), 0.7), _num(voice.get("tone"), 0.5)

    def burst(kind: str, freq: float, time: float, gain: float, q: float = 0.7) -> np.ndarray:
        n = int(time * SR) + 64
        return filt(_noise(n), kind, freq, q) * _decay(n, time) * gain

    def tonal(start: float, end: float, time: float, gain: float, kind: str = "sine") -> np.ndarray:
        n = int(time * SR) + 64
        return _sweep(n, start, end, time, kind) * _decay(n, time, 4.0) * gain

    def mix(*parts: np.ndarray) -> np.ndarray:
        size = max(len(p) for p in parts)
        out = np.zeros(size, dtype=np.float32)
        for p in parts:
            out[: len(p)] += p
        return out

    if lane == "kick":
        return mix(tonal(body * 3.2, body, 0.32 + punch * 0.18, 1.0), burst("lowpass", 900, 0.03, 0.4 * punch)) * level
    if lane == "snare":
        return mix(tonal(snare * 1.4, snare, 0.14, 0.55, "triangle"), burst("highpass", 1800 + tone * 1800, 0.18, 0.55 * snap + 0.2)) * level
    if lane == "rim":
        return tonal(1700, 900, 0.03, 0.35, "square") * level
    if lane == "clap":
        parts = [np.pad(burst("bandpass", 1500, 0.02 if i < 2 else 0.16, 0.5, 1.1), (int(i * 0.012 * SR), 0)) for i in range(3)]
        return mix(*parts) * level
    if lane == "hat":
        return burst("highpass", hat, 0.05, 0.28) * level
    if lane == "open_hat":
        return burst("highpass", hat * 0.9, 0.3, 0.26) * level
    if lane == "tom":
        return tonal(190, 110, 0.28, 0.8) * level
    if lane == "crash":
        return burst("highpass", 3200, 1.1, 0.34) * level
    if lane == "ride":
        return mix(burst("bandpass", 7000, 0.45, 0.2, 2.0), tonal(5200, 5100, 0.2, 0.08, "triangle")) * level
    if lane == "cowbell":
        return mix(tonal(810, 800, 0.2, 0.22, "square"), tonal(540, 530, 0.2, 0.22, "square")) * level
    if lane == "shaker":
        return burst("highpass", 6000, 0.07, 0.2) * level
    if lane == "conga":
        return tonal(330, 230, 0.2, 0.7) * level
    if lane == "bongo":
        return tonal(480, 360, 0.12, 0.65) * level
    if lane == "clave":
        return tonal(2500, 2400, 0.06, 0.6) * level
    if lane == "tamb":
        return mix(burst("highpass", 8000, 0.1, 0.25), tonal(4000, 3800, 0.05, 0.1, "triangle")) * level
    return burst("bandpass", 2400, 0.1, 0.25, 1.4) * level


def riser(dur: float, vel: float) -> np.ndarray:
    n = max(1, int(dur * SR))
    out = np.zeros(n, dtype=np.float32)
    noise = _noise(n)
    for start in range(0, n, 2048):
        frac = start / n
        part = noise[start: start + 2048]
        out[start: start + len(part)] = filt(part, "bandpass", 400 * (22.5 ** frac), 1.4)
    return out * (np.linspace(0.0, 1.0, n, dtype=np.float32) ** 2) * 0.35 * vel
