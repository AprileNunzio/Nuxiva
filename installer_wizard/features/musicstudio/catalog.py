from dataclasses import dataclass, field

ROLES = ("drums", "bass", "chords", "pad", "lead", "arp", "vocal", "fx")
MODES = ("major", "minor", "dorian", "mixolydian", "pentatonic")
NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
LANES = {"kick": 36, "rim": 37, "snare": 38, "clap": 39, "hat": 42, "tom": 45, "open_hat": 46, "crash": 49, "ride": 51, "perc": 56}
GENRES = ("pop", "rock", "house", "techno", "hiphop", "trap", "lofi", "reggaeton", "disco", "ballad", "dnb", "ambient", "funk", "latin")


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


INSTRUMENTS: tuple[Instrument, ...] = (
    Instrument("kit_acoustic", "Batteria acustica", "drums", "#f97316", kit(52, 190, 7600, 0.8, 0.7, 0.5, 0.1), ("batteria", "drums", "acoustic", "rock", "pop")),
    Instrument("kit_808", "Batteria 808", "drums", "#ef4444", kit(44, 170, 8200, 1.0, 0.5, 0.35, 0.3), ("808", "trap", "hiphop", "sub")),
    Instrument("kit_electro", "Batteria elettronica", "drums", "#f59e0b", kit(58, 210, 9000, 0.9, 0.9, 0.6, 0.2), ("electro", "house", "techno", "dance")),
    Instrument("kit_lofi", "Batteria lo-fi", "drums", "#d97706", kit(50, 180, 6200, 0.6, 0.4, 0.4, 0.6), ("lofi", "chill", "dusty")),
    Instrument("bass_sub", "Basso sub", "bass", "#8b5cf6", synth([osc("sine", 1.0), osc("sine", 0.35, 0, 1)], 0.005, 0.2, 0.9, 0.12, 900, 0.7, 0.0, True), ("sub", "808", "basso", "bass")),
    Instrument("bass_saw", "Basso synth", "bass", "#7c3aed", synth([osc("sawtooth", 0.8), osc("square", 0.5, 6, -1)], 0.004, 0.22, 0.55, 0.1, 1600, 2.4, 1400, True), ("synth", "basso", "bass", "house", "funk")),
    Instrument("bass_pluck", "Basso pizzicato", "bass", "#6d28d9", synth([osc("triangle", 1.0), osc("sawtooth", 0.3)], 0.002, 0.28, 0.2, 0.1, 1100, 1.2, 1800, True), ("pluck", "basso", "bass", "pop", "rock")),
    Instrument("keys_electric", "Piano elettrico", "chords", "#0ea5e9", synth([osc("sine", 0.9), osc("triangle", 0.45, 3, 1)], 0.004, 0.9, 0.35, 0.5, 5200, 0.9, 1500), ("piano", "keys", "electric", "soul", "lofi")),
    Instrument("keys_piano", "Pianoforte", "chords", "#38bdf8", synth([osc("triangle", 0.9), osc("sine", 0.5, 2, 1), osc("sine", 0.2, -3, 2)], 0.003, 1.1, 0.18, 0.45, 7000, 0.8, 2500), ("piano", "pianoforte", "ballad", "pop")),
    Instrument("organ", "Organo", "chords", "#06b6d4", synth([osc("sine", 0.7), osc("sine", 0.5, 0, 1), osc("sine", 0.3, 0, 2)], 0.01, 0.05, 1.0, 0.08, 6500), ("organo", "organ", "gospel", "rock")),
    Instrument("pad_warm", "Pad caldo", "pad", "#14b8a6", synth([osc("sawtooth", 0.5, -8), osc("sawtooth", 0.5, 8), osc("triangle", 0.4, 0, -1)], 0.7, 0.8, 0.8, 1.4, 1900, 0.8, 700), ("pad", "warm", "ambient", "atmosfera")),
    Instrument("pad_glass", "Pad cristallo", "pad", "#2dd4bf", synth([osc("triangle", 0.6, -5, 1), osc("sine", 0.6, 5, 2), osc("sawtooth", 0.2, 0)], 0.9, 1.0, 0.7, 1.8, 6500, 0.9, 900), ("pad", "glass", "ethereal", "ambient")),
    Instrument("strings", "Archi", "pad", "#10b981", synth([osc("sawtooth", 0.6, -10), osc("sawtooth", 0.6, 10), osc("sawtooth", 0.3, 0, 1)], 0.35, 0.5, 0.85, 0.6, 3200, 0.7, 500), ("archi", "strings", "cinematic", "ballad")),
    Instrument("lead_saw", "Lead synth", "lead", "#ec4899", synth([osc("sawtooth", 0.7, -7), osc("sawtooth", 0.7, 7)], 0.01, 0.2, 0.7, 0.2, 4200, 1.4, 2200, True, 0.03), ("lead", "synth", "melodia", "dance")),
    Instrument("lead_square", "Lead 8-bit", "lead", "#f43f5e", synth([osc("square", 0.8)], 0.005, 0.1, 0.8, 0.1, 6200, 0.6, 0, True), ("lead", "retro", "chiptune", "8bit")),
    Instrument("lead_bell", "Campana", "lead", "#db2777", synth([osc("sine", 0.8), osc("sine", 0.35, 0, 2), osc("sine", 0.2, 0, 3)], 0.002, 1.4, 0.0, 1.2, 9000), ("bell", "campana", "lofi", "ambient")),
    Instrument("lead_flute", "Flauto", "lead", "#e879f9", synth([osc("sine", 1.0), osc("triangle", 0.25, 0, 1)], 0.06, 0.2, 0.8, 0.2, 5200, 0.6, 0, True, 0.04), ("flute", "flauto", "melodia", "folk")),
    Instrument("arp_pluck", "Arpeggio pizzicato", "arp", "#a855f7", synth([osc("sawtooth", 0.6), osc("square", 0.3, 5)], 0.002, 0.18, 0.0, 0.12, 3600, 1.8, 2600), ("arp", "arpeggio", "pluck", "dance")),
    Instrument("fx_sweep", "Sweep e riser", "fx", "#64748b", {"engine": "noise", "sweep": 1}, ("riser", "sweep", "fx", "effetto")),
    Instrument("voice_tts", "Voce", "vocal", "#22c55e", {"engine": "voice"}, ("voce", "vocal", "cantato", "rap", "parlato")),
)

BY_ID = {i.id: i for i in INSTRUMENTS}
DEFAULT_INSTRUMENT = {"drums": "kit_acoustic", "bass": "bass_pluck", "chords": "keys_electric", "pad": "pad_warm", "lead": "lead_saw", "arp": "arp_pluck", "vocal": "voice_tts", "fx": "fx_sweep"}


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


EFFECTS: tuple[Effect, ...] = (
    Effect("eq3", "Equalizzatore 3 bande", {"low": Knob(-18, 18, 0, "dB"), "mid": Knob(-18, 18, 0, "dB"), "high": Knob(-18, 18, 0, "dB")}, ("eq", "equalizzatore", "toni")),
    Effect("filter", "Filtro", {"cutoff": Knob(80, 18000, 8000, "Hz"), "q": Knob(0.1, 18, 0.9), "type": Knob(0, 2, 0)}, ("filtro", "lowpass", "highpass", "passa basso")),
    Effect("delay", "Eco", {"time": Knob(0.0625, 2, 0.375, "beat"), "feedback": Knob(0, 0.92, 0.35), "mix": Knob(0, 1, 0.25)}, ("eco", "delay", "ripetizione")),
    Effect("reverb", "Riverbero", {"size": Knob(0.2, 6, 2.2, "s"), "damp": Knob(0, 1, 0.4), "mix": Knob(0, 1, 0.25)}, ("riverbero", "reverb", "sala", "spazio")),
    Effect("chorus", "Chorus", {"rate": Knob(0.1, 8, 0.8, "Hz"), "depth": Knob(0, 1, 0.5), "mix": Knob(0, 1, 0.4)}, ("chorus", "ensemble", "larghezza")),
    Effect("distortion", "Distorsione", {"drive": Knob(0, 1, 0.4), "tone": Knob(0, 1, 0.6), "mix": Knob(0, 1, 0.5)}, ("distorsione", "saturazione", "overdrive", "grinta")),
    Effect("compressor", "Compressore", {"threshold": Knob(-60, 0, -18, "dB"), "ratio": Knob(1, 20, 4), "attack": Knob(0.001, 0.2, 0.01, "s"), "release": Knob(0.02, 1, 0.2, "s")}, ("compressore", "dinamica", "volume")),
    Effect("phaser", "Phaser", {"rate": Knob(0.05, 6, 0.5, "Hz"), "depth": Knob(0, 1, 0.6), "mix": Knob(0, 1, 0.5)}, ("phaser", "sweep", "movimento")),
)
EFFECT_BY_ID = {e.id: e for e in EFFECTS}


def public() -> dict:
    return {
        "roles": list(ROLES), "modes": list(MODES), "genres": list(GENRES), "notes": list(NOTE_NAMES), "lanes": LANES,
        "instruments": [{"id": i.id, "name": i.name, "role": i.role, "color": i.color, "voice": i.voice, "tags": list(i.tags)} for i in INSTRUMENTS],
        "effects": [{"id": e.id, "name": e.name, "tags": list(e.tags),
                     "knobs": {k: {"min": v.low, "max": v.high, "default": v.default, "unit": v.unit} for k, v in e.knobs.items()}} for e in EFFECTS],
    }
