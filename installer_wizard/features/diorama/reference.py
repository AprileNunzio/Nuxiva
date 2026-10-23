from dataclasses import dataclass
from typing import Callable

from features.diorama import learned
from features.diorama.catalog import BY_ID, KINDS, MOTION_NOTE, Kind, Param
from features.diorama.recall import tokens

PREFIX = {"Terreno": "TER", "Ferrovia": "FER", "Architettura": "ARC", "Vegetazione": "VEG", "Arredo": "ARR", "Libero": "LIB", "Appresi": "APP"}
UNITS = {"w": "m", "d": "m", "h": "m", "length": "m", "width": "m", "height": "m", "radius": "m", "top": "m", "car_length": "m", "count": "pz",
         "density": "0-1", "bloom": "0-1", "tracks": "pz", "cars": "pz"}
MOVERS = ("train", "person", "car")
FULL_LIMIT = 10

Dims = Callable[[dict], tuple[float, float, float]]


@dataclass(frozen=True)
class Entry:
    english: str
    tags: tuple[str, ...]
    material: str
    related: tuple[str, ...] = ()
    anchor: str = "suolo"


ENTRIES: dict[str, Entry] = {
    "grass_patch": Entry("Grass patch", ("erba", "prato", "fiori", "campo", "verde", "grass", "lawn", "meadow", "flowers"), "grass", ("path", "bush", "pond")),
    "path": Entry("Path", ("sentiero", "viottolo", "camminamento", "ghiaia", "path", "walkway", "gravel"), "concrete", ("lamp", "bench", "fence")),
    "pond": Entry("Pond", ("stagno", "lago", "acqua", "laghetto", "pond", "water", "lake"), "glass", ("rock", "bush", "tree_cherry")),
    "rock": Entry("Rock", ("sasso", "masso", "pietra", "scoglio", "rock", "boulder", "stone"), "stone", ("pond", "grass_patch")),
    "petals": Entry("Fallen petals", ("petali", "fiori", "primavera", "sakura", "petals", "blossom", "spring"), "paint", ("tree_cherry",)),
    "platform": Entry("Station platform", ("banchina", "marciapiede", "stazione", "binario", "platform", "station"), "concrete", ("rails", "canopy", "bench", "sign", "vending")),
    "rails": Entry("Railway tracks", ("binari", "rotaie", "ferrovia", "traversine", "treno", "rails", "railway", "track"), "metal", ("train", "platform", "crossing")),
    "train": Entry("Train", ("treno", "convoglio", "vagone", "carrozza", "locomotiva", "metro", "train", "railcar", "locomotive"), "paint", ("rails", "platform", "crossing"), "binario"),
    "station_building": Entry("Station building", ("stazione", "edificio", "biglietteria", "station", "building", "terminal"), "wood", ("platform", "sign", "lamp")),
    "canopy": Entry("Platform canopy", ("pensilina", "tettoia", "riparo", "canopy", "shelter", "roof"), "metal", ("platform", "bench")),
    "footbridge": Entry("Footbridge", ("passerella", "cavalcavia", "ponte", "scale", "footbridge", "bridge", "overpass"), "metal", ("rails", "platform")),
    "house": Entry("House", ("casa", "abitazione", "villetta", "tetto", "house", "home", "cottage"), "wood", ("fence", "tree_maple", "bush", "path")),
    "crossing": Entry("Level crossing", ("passaggio", "livello", "barriera", "semaforo", "crossing", "barrier", "gate"), "metal", ("rails", "road", "train")),
    "tree_cherry": Entry("Cherry blossom tree", ("ciliegio", "sakura", "albero", "fiori", "primavera", "cherry", "tree", "blossom"), "wood", ("petals", "bench", "path")),
    "tree_pine": Entry("Pine tree", ("pino", "abete", "conifera", "albero", "bosco", "pine", "fir", "conifer", "tree"), "wood", ("rock", "grass_patch")),
    "tree_maple": Entry("Maple tree", ("acero", "autunno", "albero", "foglie", "maple", "autumn", "tree"), "wood", ("bench", "path", "house")),
    "bush": Entry("Bush", ("cespuglio", "arbusto", "siepe", "bush", "shrub", "hedge"), "grass", ("fence", "path", "house")),
    "lamp": Entry("Street lamp", ("lampione", "lampada", "luce", "illuminazione", "lamp", "light", "streetlight"), "metal", ("path", "road", "platform")),
    "bench": Entry("Bench", ("panchina", "sedile", "seduta", "bench", "seat"), "wood", ("path", "tree_cherry", "platform")),
    "fence": Entry("Fence", ("recinzione", "staccionata", "ringhiera", "cancello", "fence", "railing"), "metal", ("path", "house", "rails")),
    "road": Entry("Road", ("strada", "asfalto", "via", "carreggiata", "road", "street", "asphalt"), "asphalt", ("car", "lamp", "crossing")),
    "vending": Entry("Vending machine", ("distributore", "bibite", "macchinetta", "vending", "machine", "drinks"), "paint", ("platform", "sign")),
    "sign": Entry("Sign", ("cartello", "insegna", "segnale", "scritta", "sign", "signpost", "board"), "metal", ("platform", "road")),
    "person": Entry("Person", ("persona", "uomo", "donna", "passeggero", "pedone", "person", "people", "passenger", "pedestrian"), "plastic", ("platform", "path", "bench"), "suolo"),
    "car": Entry("Car", ("auto", "macchina", "automobile", "veicolo", "car", "vehicle"), "paint", ("road", "crossing"), "strada"),
    "block": Entry("Free block", ("blocco", "cubo", "parallelepipedo", "muro", "edificio", "block", "box", "wall", "custom"), "concrete", ("cylinder",)),
    "cylinder": Entry("Free cylinder", ("cilindro", "cono", "colonna", "torre", "serbatoio", "cylinder", "cone", "column", "tower"), "concrete", ("block",)),
}

DIMS: dict[str, Dims] = {
    "grass_patch": lambda p: (p["w"], p["d"], 0.15),
    "path": lambda p: (p["w"], p["d"], 0.04),
    "pond": lambda p: (p["w"], p["d"], 0.12),
    "rock": lambda p: (p["radius"] * 2, p["radius"] * 2, p["radius"] * 1.6),
    "petals": lambda p: (p["w"], p["d"], 0.02),
    "platform": lambda p: (p["length"], p["width"], p["height"]),
    "rails": lambda p: (p["length"], 1.1 * p["tracks"], 0.14),
    "train": lambda p: (p["cars"] * (p["car_length"] + 0.06), 0.84, 1.05),
    "station_building": lambda p: (p["w"], p["d"], p["h"] * 1.4),
    "canopy": lambda p: (p["length"], p["width"], p["height"] + 0.15),
    "footbridge": lambda p: (p["length"], 1.2, p["height"] + 0.9),
    "house": lambda p: (p["w"], p["d"], p["h"] * 1.5),
    "crossing": lambda p: (p["width"] + 0.5, 1.3, 0.65),
    "tree_cherry": lambda p: (p["height"] * 0.75, p["height"] * 0.75, p["height"]),
    "tree_pine": lambda p: (p["height"] * 0.45, p["height"] * 0.45, p["height"]),
    "tree_maple": lambda p: (p["height"] * 0.7, p["height"] * 0.7, p["height"]),
    "bush": lambda p: (p["radius"] * 2, p["radius"] * 2, p["radius"] * 1.6),
    "lamp": lambda p: (0.3, 0.3, p["height"]),
    "bench": lambda p: (p["length"], 0.34, 0.58),
    "fence": lambda p: (p["length"], 0.06, p["height"]),
    "road": lambda p: (p["length"], p["width"], 0.03),
    "vending": lambda p: (0.42, 0.3, 0.72),
    "sign": lambda p: (0.62, 0.06, p["height"]),
    "person": lambda p: (0.23 * p["height"] / 0.75, 0.15 * p["height"] / 0.75, p["height"]),
    "car": lambda p: (1.5, 0.68, 0.5),
    "block": lambda p: (p["w"], p["d"], p["h"]),
    "cylinder": lambda p: (max(p["radius"], p["top"]) * 2, max(p["radius"], p["top"]) * 2, p["h"]),
}


def _defaults(kind: Kind) -> dict:
    return {name: p.default for name, p in kind.params.items()}


def _param(p: Param, unit: str) -> dict:
    unit = unit or {"color": "hex", "number": "-"}.get(p.kind, "")
    return {"type": p.kind, "default": p.default, "min": p.low, "max": p.high, "choices": list(p.choices), "unit": unit}


def _codes() -> dict[str, str]:
    counters: dict[str, int] = {}
    out = {}
    for kind in KINDS:
        prefix = PREFIX.get(kind.group, "GEN")
        counters[prefix] = counters.get(prefix, 0) + 1
        out[kind.id] = f"{prefix}-{counters[prefix]:02d}"
    return out


CODES = _codes()


def _size(kind: Kind) -> dict:
    w, d, h = DIMS[kind.id](_defaults(kind))
    return {"w": round(w, 2), "d": round(d, 2), "h": round(h, 2), "unit": "m"}


def _built_in(kind: Kind) -> dict:
    entry = ENTRIES[kind.id]
    movable = kind.id in MOVERS
    return {"id": kind.id, "code": CODES[kind.id], "label": kind.label, "english": entry.english, "group": kind.group, "hint": kind.hint,
            "tags": list(entry.tags), "material": entry.material, "anchor": entry.anchor, "size": _size(kind),
            "palette": {n: p.default for n, p in kind.params.items() if p.kind == "color"},
            "params": {n: _param(p, UNITS.get(n, "")) for n, p in kind.params.items()},
            "motion": {"capable": movable, "axis": ["x", "z"], "speed": [-4, 4], "span": [4, 60]} if movable else {"capable": False},
            "related": list(entry.related), "learned": False}


def _learned_code(kind: str) -> str:
    order = sorted(learned.load().items(), key=lambda pair: (pair[1]["created"], pair[0]))
    return f"APP-{[k for k, _ in order].index(kind) + 1:02d}"


def _learned(kind: str, row: dict) -> dict:
    recipe = row["recipe"]
    return {"id": kind, "code": _learned_code(kind), "label": row["label"], "english": row["label"], "group": "Appresi",
            "hint": row["hint"], "tags": sorted(tokens(f"{row['label']} {row['hint']}")), "material": "paint", "anchor": "suolo",
            "size": {"w": 0, "d": 0, "h": 0, "unit": "m"}, "palette": {}, "params": {"color": {"type": "color", "default": "#b0b0b0", "min": 0, "max": 0, "choices": [], "unit": "hex"}},
            "motion": {"capable": bool(recipe.get("mover"))}, "related": [], "learned": True}


def catalog() -> list[dict]:
    rows = [_built_in(k) for k in KINDS]
    rows += [_learned(k, row) for k, row in learned.load().items()]
    return rows


def describe(kind: str) -> dict | None:
    if kind in BY_ID:
        return _built_in(BY_ID[kind])
    row = learned.load().get(kind)
    return _learned(kind, row) if row else None


def _document(row: dict) -> frozenset[str]:
    return tokens(" ".join([row["id"].replace("_", " "), row["label"], row["english"], row["group"], row["hint"], *row["tags"]]))


def search(query: str, limit: int = 12) -> list[dict]:
    wanted = tokens(query)
    if not wanted:
        return []
    scored = []
    for row in catalog():
        hits = len(wanted & _document(row))
        if hits:
            scored.append((hits + (0.5 if wanted & tokens(" ".join(row["tags"])) else 0), row))
    scored.sort(key=lambda pair: (-pair[0], pair[1]["code"]))
    return [row for _, row in scored[:limit]]


def _spec(row: dict) -> str:
    parts = []
    for name, p in row["params"].items():
        if p["type"] == "number":
            parts.append(f"{name}:{p['min']:g}-{p['max']:g}{p['unit'] if p['unit'] != '-' else ''}")
        elif p["type"] == "choice":
            parts.append(f"{name}:{'|'.join(p['choices'])}")
        elif p["type"] == "color":
            parts.append(f"{name}:#hex={p['default']}")
        elif p["type"] == "flag":
            parts.append(f"{name}:bool")
        else:
            parts.append(f"{name}:text")
    s = row["size"]
    size = f" size {s['w']:g}x{s['d']:g}x{s['h']:g}m" if s["w"] else ""
    return f"- {row['id']} [{row['code']}] {row['english']} ({row['hint']}){size} params {{{', '.join(parts)}}}"


def prompt_catalog(brief: str = "") -> str:
    rows = catalog()
    by_id = {r["id"]: r for r in rows}
    chosen: list[str] = [r["id"] for r in search(brief, FULL_LIMIT)]
    for kind in list(chosen[:4]):
        chosen += [rel for rel in by_id.get(kind, {}).get("related", []) if rel not in chosen]
    chosen = list(dict.fromkeys([*chosen, "block", "cylinder"]))[:FULL_LIMIT + 6] if brief.strip() else [r["id"] for r in rows]
    lines = [_spec(by_id[k]) for k in chosen if k in by_id]
    rest = [r["id"] for r in rows if r["id"] not in chosen]
    if rest:
        lines.append("Also valid with default params: " + ", ".join(rest))
    return "\n".join(lines) + "\n" + MOTION_NOTE
