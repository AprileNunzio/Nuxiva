import copy
import re
import unicodedata

from features.models3d.mesh import SHAPES, placed

KEYS = ("name", "shape", "size", "radius", "radius_top", "radius_bottom", "height", "tube", "position", "rotation", "scale", "color", "metal")
LIMIT = 10000.0
MAX_PARTS = 60
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
AXES = {"x": 0, "y": 1, "z": 2}
DEFAULTS = {
    "box": {"size": [10.0, 10.0, 10.0]},
    "wedge": {"size": [10.0, 10.0, 10.0]},
    "cylinder": {"radius": 5.0, "height": 10.0},
    "cone": {"radius": 5.0, "height": 10.0},
    "capsule": {"radius": 3.0, "height": 12.0},
    "sphere": {"radius": 5.0},
    "torus": {"radius": 5.0, "tube": 1.2},
}
COLORS = {
    "rosso": "#e03131", "blu": "#1c64f2", "azzurro": "#29b6f6", "verde": "#2f9e44", "giallo": "#f5c518", "arancione": "#f08c00",
    "viola": "#7048e8", "rosa": "#f06595", "marrone": "#8b5a2b", "nero": "#1f2933", "bianco": "#f4f1ea", "grigio": "#9aa4b2",
    "argento": "#c0c8d2", "oro": "#d4af37", "ciano": "#29e0ff",
}
SHAPE_WORDS = {
    "cubo": "box", "scatola": "box", "parallelepipedo": "box", "blocco": "box", "cilindro": "cylinder", "tubo": "cylinder",
    "cono": "cone", "sfera": "sphere", "palla": "sphere", "toro": "torus", "ciambella": "torus", "anello": "torus",
    "capsula": "capsule", "cuneo": "wedge", "rampa": "wedge",
}


class PartError(ValueError):
    pass


def norm(text: str) -> str:
    base = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9% ]+", " ", base).strip()


def _number(value, low=-LIMIT, high=LIMIT) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise PartError("Valore numerico non valido")
    if number != number or number in (float("inf"), float("-inf")):
        raise PartError("Valore numerico non valido")
    return round(max(low, min(high, number)), 3)


def _vector(value, low=-LIMIT, high=LIMIT) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise PartError("Atteso un vettore di tre valori")
    return [_number(v, low, high) for v in value]


def clean(part) -> dict:
    if not isinstance(part, dict) or part.get("shape") not in SHAPES:
        raise PartError("Forma non valida")
    out: dict = {"shape": part["shape"]}
    for key in KEYS:
        if key not in part or key == "shape":
            continue
        value = part[key]
        if key == "name":
            out[key] = re.sub(r"\s+", " ", str(value))[:40].strip() or part["shape"]
        elif key == "color":
            if not HEX.match(str(value)):
                raise PartError("Colore non valido")
            out[key] = str(value).lower()
        elif key == "metal":
            out[key] = bool(value)
        elif key in ("size", "position", "rotation", "scale"):
            out[key] = _vector(value, 0.01 if key in ("size", "scale") else -LIMIT)
        else:
            out[key] = _number(value, 0.01, LIMIT)
    return out


def unique_name(parts: list[dict], base: str) -> str:
    taken = {p.get("name") for p in parts}
    if base not in taken:
        return base
    n = 2
    while f"{base} {n}" in taken:
        n += 1
    return f"{base} {n}"


def fresh(parts: list[dict], shape: str, color: str = "#29e0ff", name: str = "", size: float = 0.0) -> dict:
    if shape not in SHAPES:
        raise PartError("Forma non valida")
    if len(parts) >= MAX_PARTS:
        raise PartError("Numero massimo di parti raggiunto")
    part = {"shape": shape, **copy.deepcopy(DEFAULTS[shape]), "color": color, "position": [0.0, 0.0, 0.0], "name": name or shape}
    part["name"] = unique_name(parts, part["name"])
    if size:
        resize_to(part, size)
    part["position"] = [0.0, round(extent(part)[1] / 2, 3), 0.0]
    return clean(part)


def corners(part: dict) -> list[tuple]:
    return placed(part).pos


def extent(part: dict) -> list[float]:
    pos = corners(part)
    return [round(max(p[i] for p in pos) - min(p[i] for p in pos), 3) for i in range(3)]


def bounds(parts: list[dict]) -> dict:
    pos = [p for part in parts for p in corners(part)]
    if not pos:
        return {"min": [0, 0, 0], "max": [0, 0, 0], "size": [0, 0, 0]}
    low = [round(min(p[i] for p in pos), 3) for i in range(3)]
    high = [round(max(p[i] for p in pos), 3) for i in range(3)]
    return {"min": low, "max": high, "size": [round(high[i] - low[i], 3) for i in range(3)]}


def measures(parts: list[dict]) -> dict:
    return {"overall": bounds(parts), "parts": [{"name": p.get("name", p["shape"]), "size": extent(p)} for p in parts]}


def resize_to(part: dict, longest: float) -> None:
    current = max(extent(part)) or 1.0
    scale = part.get("scale") or [1.0, 1.0, 1.0]
    factor = longest / current
    part["scale"] = [round(max(0.01, s * factor), 4) for s in scale]


def find(parts: list[dict], words: str) -> int | None:
    query = norm(words)
    query = re.sub(r"\b(il|lo|la|l|i|gli|le|un|una|uno|del|della|dello|dei|delle|di|parte|pezzo)\b", " ", query).strip()
    if not query or not parts:
        return None
    if query in ("ultimo", "ultima", "ultimo pezzo"):
        return len(parts) - 1
    names = [norm(p.get("name", p["shape"])) for p in parts]
    for i, name in enumerate(names):
        if name == query:
            return i
    for i, name in enumerate(names):
        if query in name or name in query:
            return i
    tokens = set(query.split())
    scored = sorted(((len(tokens & set(n.split())), -i) for i, n in enumerate(names)), reverse=True)
    best = scored[0]
    return -best[1] if best[0] else None


def translate(part: dict, axis: str, delta: float) -> None:
    position = list(part.get("position") or [0.0, 0.0, 0.0])
    position[AXES[axis]] = round(position[AXES[axis]] + delta, 3)
    part["position"] = position


def rotate(part: dict, axis: str, degrees: float) -> None:
    rotation = list(part.get("rotation") or [0.0, 0.0, 0.0])
    rotation[AXES[axis]] = round((rotation[AXES[axis]] + degrees) % 360, 3)
    part["rotation"] = rotation


def scale_by(part: dict, factor: float, axis: str | None = None) -> None:
    if factor <= 0:
        raise PartError("Fattore di scala non valido")
    scale = list(part.get("scale") or [1.0, 1.0, 1.0])
    for i in ([AXES[axis]] if axis else range(3)):
        scale[i] = round(max(0.01, min(LIMIT, scale[i] * factor)), 4)
    part["scale"] = scale


def set_dimension(part: dict, axis: str, value: float) -> None:
    current = extent(part)[AXES[axis]]
    if current <= 0:
        raise PartError("Misura non modificabile")
    rotated = any(abs(v) > 1e-6 for v in (part.get("rotation") or [0, 0, 0]))
    scale_by(part, value / current, None if rotated else axis)


def ground(parts: list[dict]) -> None:
    low = bounds(parts)["min"][1]
    for part in parts:
        translate(part, "y", -low)
