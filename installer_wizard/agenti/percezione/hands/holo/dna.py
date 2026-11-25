import math

TWIST = 34.29
RISE = 3.38
GROOVE = 154.0
PHOSPHATE_R = 8.9
SUGAR_R = 7.0
MIN_PAIRS = 4
MAX_PAIRS = 40
DEFAULT = "ATGCGTACCGATTGCAGCTA"
PAIR = {"A": "T", "T": "A", "G": "C", "C": "G"}
COLOR = {"A": "#ef476f", "T": "#ffd166", "G": "#06d6a0", "C": "#118ab2"}
KEY = {"A": "dna_adenine", "T": "dna_thymine", "G": "dna_guanine", "C": "dna_cytosine"}


def sequence(raw: str) -> str:
    clean = "".join(c for c in str(raw or "").upper() if c in PAIR)[:MAX_PAIRS]
    return clean if len(clean) >= MIN_PAIRS else DEFAULT


def _point(radius: float, angle: float, y: float) -> list[float]:
    a = math.radians(angle)
    return [radius * math.cos(a), y, radius * math.sin(a)]


def _lerp(a, b, t):
    return [x + (y - x) * t for x, y in zip(a, b)]


def _rod(name, start, end, radius, color, layer):
    d = [b - a for a, b in zip(start, end)]
    length = max(1e-4, math.sqrt(sum(v * v for v in d)))
    z = math.degrees(math.asin(max(-1.0, min(1.0, -d[0] / length))))
    x = math.degrees(math.atan2(d[2], d[1]))
    return {"name": name, "shape": "cylinder", "radius": radius, "height": length, "position": _lerp(start, end, 0.5),
            "rotation": [x, 0.0, z], "color": color, "roughness": 0.35, "layer": layer}


def _ball(name, at, radius, color, layer):
    return {"name": name, "shape": "sphere", "radius": radius, "position": at, "color": color, "roughness": 0.3, "layer": layer}


def parts(seq: str) -> list[dict]:
    out, previous = [], None
    for index, base in enumerate(seq):
        partner = PAIR[base]
        y, angle = index * RISE, index * TWIST
        p1, p2 = _point(PHOSPHATE_R, angle, y), _point(PHOSPHATE_R, angle + GROOVE, y)
        s1, s2 = _point(SUGAR_R, angle + 8.0, y), _point(SUGAR_R, angle + GROOVE - 8.0, y)
        middle = _lerp(s1, s2, 0.5)
        out += [_ball("dna_phosphate", p1, 1.35, "#ff9f1c", 0), _ball("dna_phosphate", p2, 1.35, "#ff9f1c", 0),
                _ball("dna_sugar", s1, 1.1, "#c9ada7", 0), _ball("dna_sugar", s2, 1.1, "#c9ada7", 0),
                _rod(KEY[base], s1, middle, 0.75, COLOR[base], 1), _rod(KEY[partner], middle, s2, 0.75, COLOR[partner], 1),
                _ball("dna_hydrogen_bond", middle, 0.45, "#e0fbfc", 1)]
        if previous:
            out += [_rod("dna_backbone", previous[0], p1, 0.55, "#8ecae6", 0), _rod("dna_backbone", previous[1], p2, 0.55, "#8ecae6", 0)]
        previous = (p1, p2)
    return out
