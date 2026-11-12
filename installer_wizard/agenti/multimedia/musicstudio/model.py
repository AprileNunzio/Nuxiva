from dataclasses import dataclass, field


@dataclass(frozen=True)
class Instrument:
    id: str
    name: str
    role: str
    color: str
    voice: dict = field(default_factory=dict)
    tags: tuple[str, ...] = ()


def osc(kind: str, gain: float = 1.0, detune: float = 0.0, octave: int = 0) -> dict:
    return {"type": kind, "gain": gain, "detune": detune, "octave": octave}


def synth(oscs: list[dict], a: float, d: float, s: float, r: float, cutoff: float = 12000, q: float = 0.7, env: float = 0.0, mono: bool = False, glide: float = 0.0) -> dict:
    return {"engine": "synth", "oscs": oscs, "env": {"a": a, "d": d, "s": s, "r": r}, "filter": {"type": "lowpass", "cutoff": cutoff, "q": q, "env": env}, "mono": mono, "glide": glide}


def kit(kick: float, snare: float, hat: float, punch: float, snap: float, tone: float, grit: float) -> dict:
    return {"engine": "drums", "kick": kick, "snare": snare, "hat": hat, "punch": punch, "snap": snap, "tone": tone, "grit": grit}


@dataclass(frozen=True)
class Knob:
    low: float
    high: float
    default: float
    unit: str = ""


@dataclass(frozen=True)
class Effect:
    id: str
    name: str
    knobs: dict[str, Knob]
    tags: tuple[str, ...] = ()


def vib(voice: dict, rate: float, cents: float, delay: float = 0.15) -> dict:
    return {**voice, "vibrato": {"rate": rate, "cents": cents, "delay": delay}}


def breath(voice: dict, level: float) -> dict:
    return {**voice, "breath": level}
