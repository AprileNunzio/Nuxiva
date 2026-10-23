import random

SCALES = {"major": (0, 2, 4, 5, 7, 9, 11), "minor": (0, 2, 3, 5, 7, 8, 10), "dorian": (0, 2, 3, 5, 7, 9, 10), "mixolydian": (0, 2, 4, 5, 7, 9, 10),
          "pentatonic": (0, 3, 5, 7, 10), "blues": (0, 3, 5, 6, 7, 10),
          "phrygian": (0, 1, 3, 5, 7, 8, 10), "lydian": (0, 2, 4, 6, 7, 9, 11), "harmonic_minor": (0, 2, 3, 5, 7, 8, 11), "hijaz": (0, 1, 4, 5, 7, 8, 10),
          "hirajoshi": (0, 2, 3, 7, 8), "insen": (0, 1, 5, 7, 10), "major_pentatonic": (0, 2, 4, 7, 9), "bhairav": (0, 1, 4, 5, 7, 8, 11)}
BASE_MODE = {"pentatonic": "major", "blues": "mixolydian", "major_pentatonic": "major", "hirajoshi": "minor", "insen": "phrygian"}
NAMED = {
    "blues12": tuple((s, "dom7") for s in (0, 0, 0, 0, 5, 5, 0, 0, 7, 5, 0, 7)),
    "jazz251": ((2, "min7"), (7, "dom7"), (0, "maj7"), (0, "maj7")),
    "jazz_turn": ((0, "maj7"), (9, "min7"), (2, "min7"), (7, "dom7")),
    "bossa": ((0, "maj7"), (2, "min7"), (7, "dom7"), (0, "maj7")),
    "andalusian": ((0, "min"), (10, "maj"), (8, "maj"), (7, "maj")),
    "doowop": ((0, "maj"), (9, "min"), (5, "maj"), (7, "maj")),
    "reggae": ((0, "maj"), (5, "maj"), (0, "maj"), (5, "maj")),
    "salsa": ((0, "min"), (5, "min"), (7, "dom7"), (0, "min")),
    "tango": ((0, "min"), (5, "min"), (7, "dom7"), (0, "min")),
    "gospel": ((0, "maj"), (5, "maj"), (0, "maj"), (7, "dom7")),
    "canon": ((0, "maj"), (7, "maj"), (9, "min"), (4, "min"), (5, "maj"), (0, "maj"), (5, "maj"), (7, "maj")),
    "trance": ((0, "min"), (8, "maj"), (3, "maj"), (10, "maj")),
    "epic": ((0, "min"), (8, "maj"), (10, "maj"), (7, "maj")),
    "rock_power": ((0, "maj"), (10, "maj"), (5, "maj"), (0, "maj")),
    "punk": ((0, "maj"), (5, "maj"), (7, "maj"), (5, "maj")),
    "metal": ((0, "min"), (1, "maj"), (0, "min"), (3, "maj")),
    "hijaz": ((0, "maj"), (1, "maj"), (0, "maj"), (0, "maj")),
    "waltz": ((0, "maj"), (7, "maj"), (0, "maj"), (5, "maj")),
    "polka": ((0, "maj"), (0, "maj"), (7, "dom7"), (0, "maj")),
    "klezmer": ((0, "min"), (7, "maj"), (0, "min"), (5, "min")),
    "country": ((0, "maj"), (5, "maj"), (0, "maj"), (7, "dom7")),
    "funk_vamp": ((0, "dom7"), (0, "dom7"), (5, "dom7"), (0, "dom7")),
    "minor_vamp": ((0, "min7"), (0, "min7"), (8, "maj7"), (7, "dom7")),
    "tarantella": ((0, "min"), (7, "dom7"), (0, "min"), (7, "dom7")),
    "drone": ((0, "sus4"),),
}
INTERVALS = {"maj": (0, 4, 7), "min": (0, 3, 7), "dim": (0, 3, 6), "dom7": (0, 4, 7, 10), "min7": (0, 3, 7, 10), "maj7": (0, 4, 7, 11), "sus4": (0, 5, 7)}
PROGRESSIONS = {
    "major": ((0, 4, 5, 3), (0, 5, 3, 4), (0, 3, 4, 3), (0, 2, 3, 4), (3, 4, 2, 5), (0, 4, 3, 4)),
    "minor": ((0, 5, 2, 6), (0, 3, 6, 5), (0, 6, 5, 6), (0, 3, 4, 0), (0, 5, 3, 4), (0, 2, 6, 3)),
    "dorian": ((0, 3, 0, 6), (0, 1, 3, 0), (0, 3, 6, 3)),
    "mixolydian": ((0, 6, 3, 0), (0, 4, 6, 3), (0, 6, 0, 4)),
    "pentatonic": ((0, 3, 2, 4),),
}


def degrees(mode: str) -> tuple[int, ...]:
    return SCALES[BASE_MODE.get(mode, mode)]


def triad(root: int, mode: str, degree: int, seventh: bool = False) -> tuple[int, str]:
    scale = degrees(mode)
    base = scale[degree % 7]
    third = (scale[(degree + 2) % 7] - base) % 12
    fifth = (scale[(degree + 4) % 7] - base) % 12
    quality = "maj" if (third, fifth) == (4, 7) else "min" if (third, fifth) == (3, 7) else "dim" if (third, fifth) == (3, 6) else "maj"
    if seventh:
        sev = (scale[(degree + 6) % 7] - base) % 12
        quality = {"maj": "dom7" if sev == 10 else "maj7", "min": "min7"}.get(quality, quality)
    return (root + base) % 12, quality


def harmony(root: int, mode: str, bars: int, rng: random.Random, seventh: bool, per_chord: int = 1) -> list[dict]:
    pool = PROGRESSIONS.get(mode) or PROGRESSIONS["minor" if degrees(mode)[2] == 3 else "major"]
    cycle = rng.choice(pool)
    out = []
    bar = 0
    index = 0
    while bar < bars:
        pc, quality = triad(root, mode, cycle[index % len(cycle)], seventh)
        out.append({"bar": bar, "root": pc, "quality": quality})
        bar += per_chord
        index += 1
    return out


def named(root: int, bars: int, name: str, per_chord: int = 1) -> list[dict]:
    cycle = NAMED[name]
    return [{"bar": bar, "root": (root + cycle[(bar // per_chord) % len(cycle)][0]) % 12, "quality": cycle[(bar // per_chord) % len(cycle)][1]}
            for bar in range(0, bars, per_chord)]


def chord_at(chords: list[dict], bar: int) -> dict:
    current = chords[0] if chords else {"bar": 0, "root": 0, "quality": "maj"}
    for chord in chords:
        if chord["bar"] <= bar:
            current = chord
    return current


def voicing(chord: dict, center: int = 62, size: int = 3) -> list[int]:
    notes = [(chord["root"] + i) % 12 for i in INTERVALS[chord["quality"]]][:max(3, size)]
    out = []
    for pc in notes:
        candidates = [pc + 12 * o for o in range(3, 8)]
        out.append(min(candidates, key=lambda m: abs(m - center)))
    return sorted(out)


def scale_pitches(root: int, mode: str, low: int, high: int) -> list[int]:
    steps = {(root + s) % 12 for s in SCALES[mode]}
    return [m for m in range(low, high + 1) if m % 12 in steps]
