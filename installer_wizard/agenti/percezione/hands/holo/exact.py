import json
import math

import native_module

from agenti.hands.holo import dna, fallback

GENERATED_PARTS = 400
PARTICLE_PARTS = 96
PARTICLE_SPAN = 2.2
ALIASES = {"dna": ("dna", "adn", "acido desossiribonucleico", "acide desoxyribonucleique", "acido desoxirribonucleico",
                   "deoxyribonucleic acid", "doppia elica", "double helix", "double helice", "doble helice")}
PARTICLE_SHAPES = {"sphere": "sphere", "cylinder": "cylinder", "cone": "cone", "box": "box", "wedge": "box",
                   "capsule": "cylinder", "torus": "torus", "helix": "helix", "spiral": "spiral"}


def kind_of(subject: str) -> str | None:
    from agenti.hands.holo.commands import norm
    padded = norm(subject)
    for kind, names in ALIASES.items():
        if any(norm(name) in padded for name in names):
            return kind
    return None


def _build(kind: str, detail: str) -> dict:
    engine = native_module.feature("holo_dna")
    if engine is not None:
        return json.loads(engine(detail))
    native_module.python_fallback("holo")
    return fallback.prepare({"title": "DNA", "source": "model", "parts": dna.parts(dna.sequence(detail))}, GENERATED_PARTS)


def _prefixed(names: dict, name: str) -> dict | None:
    stem, _, tail = name.rpartition("_")
    entry = names.get(stem) if stem and len(tail) == 1 else None
    if not entry:
        return None
    return {"label": entry["label"].replace("{chain}", tail), "info": entry.get("info", "").replace("{chain}", tail)}


def localize(scene: dict, lang: str) -> dict:
    from agenti.hands.holo.commands import vocab
    names = vocab(lang).get("parts", {})
    for part in scene["parts"]:
        entry = names.get(part["name"]) or _prefixed(names, part["name"])
        if entry:
            part["label"], part["info"] = entry["label"], entry.get("info", "")
    title = names.get(scene.get("title", "").lower())
    if title:
        scene["title"] = title["label"]
    return scene


def scene(kind: str, lang: str, detail: str = "") -> dict:
    return localize(_build(kind, detail), lang)


def _zyx(rot_xyz: list[float]) -> list[float]:
    a, b, c = (math.radians(v) for v in rot_xyz)
    ca, sa, cb, sb, cc, sc = math.cos(a), math.sin(a), math.cos(b), math.sin(b), math.cos(c), math.sin(c)
    m = [[cb * cc, -cb * sc, sb],
         [ca * sc + sa * sb * cc, ca * cc - sa * sb * sc, -sa * cb],
         [sa * sc - ca * sb * cc, sa * cc + ca * sb * sc, ca * cb]]
    r20, r21, r22 = m[2]
    y = math.asin(max(-1.0, min(1.0, -r20)))
    x = math.atan2(r21, r22)
    z = math.atan2(m[1][0], m[0][0])
    return [round(math.degrees(v), 3) for v in (x, y, z)]


def to_particles(holo: dict) -> dict:
    ranked = sorted(holo["parts"], key=lambda p: (p["name"] in ("dna_backbone", "dna_sugar", "dna_hydrogen_bond"), -max(p["half"])))
    out = []
    for part in ranked[:PARTICLE_PARTS]:
        rot = part["rot"] if holo.get("euler") == "ZYX" else _zyx(part["rot"])
        out.append({"shape": PARTICLE_SHAPES.get(part["shape"], "sphere"),
                    "size": [round(max(0.01, min(10.0, h * PARTICLE_SPAN)), 4) for h in part["half"]],
                    "at": [round(max(-10.0, min(10.0, v * PARTICLE_SPAN)), 4) for v in part["at"]],
                    "rot": [max(-360.0, min(360.0, v)) for v in rot], "color": part["color"],
                    "weight": round(max(0.2, min(3.0, 0.4 + max(part["half"]) * 4)), 3)})
    return {"parts": out}
