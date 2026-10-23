import random

SCALES = {"major": (0, 2, 4, 5, 7, 9, 11), "minor": (0, 2, 3, 5, 7, 8, 10), "dorian": (0, 2, 3, 5, 7, 9, 10), "mixolydian": (0, 2, 4, 5, 7, 9, 10),
          "pentatonic": (0, 3, 5, 7, 10), "blues": (0, 3, 5, 6, 7, 10)}
INTERVALS = {"maj": (0, 4, 7), "min": (0, 3, 7), "dim": (0, 3, 6), "dom7": (0, 4, 7, 10), "min7": (0, 3, 7, 10), "maj7": (0, 4, 7, 11), "sus4": (0, 5, 7)}
PROGRESSIONS = {
    "major": ((0, 4, 5, 3), (0, 5, 3, 4), (0, 3, 4, 3), (0, 2, 3, 4), (3, 4, 2, 5), (0, 4, 3, 4)),
    "minor": ((0, 5, 2, 6), (0, 3, 6, 5), (0, 6, 5, 6), (0, 3, 4, 0), (0, 5, 3, 4), (0, 2, 6, 3)),
    "dorian": ((0, 3, 0, 6), (0, 1, 3, 0), (0, 3, 6, 3)),
    "mixolydian": ((0, 6, 3, 0), (0, 4, 6, 3), (0, 6, 0, 4)),
    "pentatonic": ((0, 3, 2, 4),),
}


def degrees(mode: str) -> tuple[int, ...]:
    return SCALES["major" if mode == "pentatonic" else "mixolydian" if mode == "blues" else mode]


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
    pool = PROGRESSIONS[mode]
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


BLUES_BARS = ((0, 0, 0, 0), (5, 5, 0, 0), (7, 5, 0, 7))


def blues(root: int, bars: int) -> list[dict]:
    steps = [degree for row in BLUES_BARS for degree in row]
    return [{"bar": bar, "root": (root + steps[bar % 12]) % 12, "quality": "dom7"} for bar in range(bars)]


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
