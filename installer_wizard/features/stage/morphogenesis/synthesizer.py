import json
import math
import re

from features.stage import native, particles

PREFIXES = (
    "creami con delle particelle",
    "crea con delle particelle",
    "crea con le particelle",
    "mostrami con le particelle",
    "mostrami in particelle",
    "fammi vedere come e fatta",
    "fammi vedere come è fatta",
    "fammi vedere come e fatto",
    "fammi vedere come è fatto",
    "mi dici come e fatta",
    "mi dici come è fatta",
    "mi dici come e fatto",
    "mi dici come è fatto",
    "mi spieghi come e fatta",
    "mi spieghi come è fatta",
    "mi spieghi come e fatto",
    "mi spieghi come è fatto",
    "spiegami come e fatta",
    "spiegami come è fatta",
    "spiegami come e fatto",
    "spiegami come è fatto",
    "come sono fatte",
    "come sono fatti",
    "come e strutturata",
    "come è strutturata",
    "come e strutturato",
    "come è strutturato",
    "com'e strutturata",
    "com'è strutturata",
    "com'e strutturato",
    "com'è strutturato",
    "come e composta",
    "come è composta",
    "come e composto",
    "come è composto",
    "come e fatta",
    "come è fatta",
    "come e fatto",
    "come è fatto",
    "com'e fatta",
    "com'è fatta",
    "com'e fatto",
    "com'è fatto",
    "come funziona",
    "anatomia di",
    "struttura di",
    "forma di",
    "mostrami",
    "fammi vedere",
    "visualizza",
    "ologramma di",
    "particelle di",
    "how is made",
    "how is a",
    "structure of",
    "anatomy of",
    "show me",
)

ARTICLES = frozenset({
    "un'", "uno", "una", "un", "il", "lo", "la", "i", "gli", "le", "l'", "del", "dello", "della",
    "dei", "degli", "delle", "di", "da", "in", "con", "per", "the", "an", "a", "of",
})

STOP_TAILS = (
    "con delle particelle",
    "con le particelle",
    "in particelle",
    "in 3d",
    "nel dettaglio",
    "esattamente",
    "per favore",
    "grazie",
    "made",
    "built",
    "structured",
)


def _clean_text(raw: str) -> str:
    chars = []
    for ch in str(raw or "").lower():
        if ch.isalnum() or ch in ("'", "’", "-"):
            chars.append("'" if ch == "’" else ch)
        else:
            chars.append(" ")
    return " ".join("".join(chars).split())


def _strip_articles(text: str) -> str:
    words = text.split()
    while words:
        first = words[0]
        if first.startswith("l'") or first.startswith("un'"):
            rest = first.split("'", 1)[1]
            if rest:
                words[0] = rest
            else:
                words.pop(0)
            break
        if first in ARTICLES:
            words.pop(0)
        else:
            break
    return " ".join(words[:4])


def extract_visual_concept(query: str) -> str | None:
    if native.lib is not None and hasattr(native.lib, "particles_extract_concept"):
        try:
            return native.lib.particles_extract_concept(str(query or ""))
        except Exception:
            pass
    cleaned = _clean_text(query)
    if len(cleaned) < 4:
        return None
    matched_tail = None
    for prefix in PREFIXES:
        idx = cleaned.find(prefix)
        if idx != -1:
            tail = cleaned[idx + len(prefix):].strip()
            if tail:
                matched_tail = tail
                break
    if not matched_tail:
        return None
    candidate = matched_tail
    for tail in STOP_TAILS:
        if candidate.endswith(tail):
            candidate = candidate[:-len(tail)].strip()
    subject = _strip_articles(candidate)
    return subject if len(subject) >= 2 else None


def _part(shape: str, size: list[float], at: list[float], rot: list[float], color: str, weight: float) -> dict:
    return {"shape": shape, "size": size, "at": at, "rot": rot, "color": color, "weight": weight}


def _medusa_spec() -> dict:
    parts = [
        _part("sphere", [1.35, 0.85, 1.35], [0.0, 0.95, 0.0], [0.0, 0.0, 0.0], "#5ef2ff", 2.4),
        _part("torus", [1.22, 0.32, 1.22], [0.0, 0.45, 0.0], [0.0, 0.0, 0.0], "#a87bff", 1.6),
        _part("sphere", [0.68, 0.48, 0.68], [0.0, 0.82, 0.0], [0.0, 0.0, 0.0], "#ff7be5", 1.3),
        _part("cone", [0.42, 1.1, 0.42], [0.0, -0.35, 0.0], [180.0, 0.0, 0.0], "#c49bff", 1.5),
    ]
    for i in range(6):
        angle = (i / 6.0) * math.tau
        x = round(0.78 * math.cos(angle), 4)
        z = round(0.78 * math.sin(angle), 4)
        color = "#4ce6ff" if i % 2 == 0 else "#8c6bff"
        parts.append(_part("helix", [0.16, 1.35, 0.16], [x, -0.85, z], [0.0, float(i * 30), 0.0], color, 1.1))
    return {"parts": parts}


def _molecular_spec() -> dict:
    return {
        "parts": [
            _part("sphere", [0.55, 0.55, 0.55], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], "#ff6bd6", 2.0),
            _part("helix", [0.75, 1.85, 0.75], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], "#4cf2ff", 2.2),
            _part("helix", [0.75, 1.85, 0.75], [0.0, 0.0, 0.0], [0.0, 180.0, 0.0], "#9b7bff", 2.2),
            _part("torus", [1.45, 0.25, 1.45], [0.0, 0.0, 0.0], [35.0, 20.0, 0.0], "#66ffe3", 1.4),
            _part("torus", [1.45, 0.25, 1.45], [0.0, 0.0, 0.0], [-35.0, -20.0, 0.0], "#7aa2ff", 1.4),
        ]
    }


def _cosmic_spec() -> dict:
    return {
        "parts": [
            _part("sphere", [0.95, 0.95, 0.95], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], "#ffd166", 2.5),
            _part("torus", [1.85, 0.22, 1.85], [0.0, 0.0, 0.0], [22.0, 0.0, 12.0], "#5ce1e6", 2.0),
            _part("torus", [2.35, 0.16, 2.35], [0.0, 0.0, 0.0], [22.0, 0.0, 12.0], "#9b7bff", 1.5),
            _part("cone", [0.25, 1.4, 0.25], [0.0, 1.2, 0.0], [0.0, 0.0, 0.0], "#72efdd", 0.9),
            _part("cone", [0.25, 1.4, 0.25], [0.0, -1.2, 0.0], [180.0, 0.0, 0.0], "#72efdd", 0.9),
        ]
    }


def _mechanical_spec() -> dict:
    return {
        "parts": [
            _part("cylinder", [0.65, 1.55, 0.65], [0.0, 0.0, 0.0], [0.0, 0.0, 90.0], "#64dfdf", 2.2),
            _part("torus", [1.05, 0.3, 1.05], [-0.85, 0.0, 0.0], [0.0, 0.0, 90.0], "#48bfe3", 1.6),
            _part("torus", [1.05, 0.3, 1.05], [0.85, 0.0, 0.0], [0.0, 0.0, 90.0], "#48bfe3", 1.6),
            _part("cone", [0.65, 0.75, 0.65], [1.75, 0.0, 0.0], [0.0, 0.0, -90.0], "#80ffdb", 1.3),
            _part("sphere", [0.48, 0.48, 0.48], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], "#ff9f1c", 1.5),
            _part("box", [0.35, 0.08, 1.95], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], "#7400b8", 1.4),
        ]
    }


def _universal_hash_spec(concept: str) -> dict:
    h = 0xCBF29CE484222325
    for b in concept.encode("utf-8"):
        h ^= b
        h = (h * 0x0100000001B3) & 0xFFFFFFFFFFFFFFFF
    palette = ("#5ef2ff", "#9b7bff", "#66ffe3", "#ff7be5", "#7aa2ff", "#ffd166")
    core_shape = ("sphere", "cylinder", "cone")[h % 3]
    sat_shape = ("helix", "cone", "cylinder", "sphere")[(h >> 4) % 4]
    parts = [
        _part(core_shape, [1.05, 1.05, 1.05], [0.0, 0.15, 0.0], [0.0, 0.0, 0.0], palette[0], 2.2),
        _part("torus", [1.45, 0.28, 1.45], [0.0, 0.0, 0.0], [18.0, 0.0, -18.0], palette[1], 1.7),
        _part("cone", [0.5, 0.9, 0.5], [0.0, 1.15, 0.0], [0.0, 0.0, 0.0], palette[2], 1.2),
    ]
    for i in range(4):
        angle = (i / 4.0) * math.tau
        x = round(1.15 * math.cos(angle), 4)
        z = round(1.15 * math.sin(angle), 4)
        color = palette[(i + 2) % len(palette)]
        parts.append(_part(sat_shape, [0.28, 0.95, 0.28], [x, -0.45, z], [0.0, float(i * 45), 0.0], color, 1.1))
    return {"parts": parts}


def synthesize_spec(concept: str) -> dict:
    if native.lib is not None and hasattr(native.lib, "particles_synthesize_spec"):
        try:
            raw = native.lib.particles_synthesize_spec(str(concept or ""))
            return particles.validate(json.loads(raw))
        except Exception:
            pass
    lower = _clean_text(concept)
    if any(kw in lower for kw in ("medusa", "jellyfish", "polpo", "piovra", "calamaro", "anemone", "cnidario")):
        return particles.validate(_medusa_spec())
    if any(kw in lower for kw in ("dna", "atomo", "molecola", "cellula", "virus", "neurone", "proteina", "cromosoma", "batterio")):
        return particles.validate(_molecular_spec())
    if any(kw in lower for kw in ("saturno", "pianeta", "galassia", "buco nero", "stella", "sole", "sistema solare", "cometa", "pulsar")):
        return particles.validate(_cosmic_spec())
    if any(kw in lower for kw in ("motore", "turbina", "reattore", "razzo", "aereo", "drone", "elicottero", "robot", "auto", "macchina")):
        return particles.validate(_mechanical_spec())
    return particles.validate(_universal_hash_spec(lower))


def _clamp_vec(raw, default: float, lo: float, hi: float) -> list[float]:
    if not isinstance(raw, (list, tuple)) or len(raw) != 3:
        return [default] * 3
    out = []
    for item in raw:
        try:
            v = float(item)
            v = v if math.isfinite(v) else default
        except (TypeError, ValueError):
            v = default
        out.append(max(lo, min(hi, v)))
    return out


def repair_or_synthesize(concept: str, raw_spec) -> dict:
    try:
        return particles.validate(raw_spec)
    except Exception:
        pass
    if isinstance(raw_spec, dict) and isinstance(raw_spec.get("parts"), list):
        cleaned = []
        for p in raw_spec["parts"][:particles.MAX_PARTS]:
            if not isinstance(p, dict):
                continue
            shape = str(p.get("shape") or "sphere").lower()
            if shape not in particles.SHAPES:
                shape = "sphere"
            color = str(p.get("color") or "#9be7ff").strip().lower()
            if not re.match(r"^#[0-9a-f]{6}$", color):
                color = "#5ef2ff"
            try:
                w = float(p.get("weight", 1.0))
                w = max(0.05, min(10.0, w if math.isfinite(w) else 1.0))
            except (TypeError, ValueError):
                w = 1.0
            cleaned.append({
                "shape": shape,
                "size": _clamp_vec(p.get("size"), 1.0, 0.05, 3.5),
                "at": _clamp_vec(p.get("at"), 0.0, -3.5, 3.5),
                "rot": _clamp_vec(p.get("rot"), 0.0, -360.0, 360.0),
                "color": color,
                "weight": w,
            })
        if cleaned:
            try:
                return particles.validate({"parts": cleaned})
            except Exception:
                pass
    return synthesize_spec(concept)
