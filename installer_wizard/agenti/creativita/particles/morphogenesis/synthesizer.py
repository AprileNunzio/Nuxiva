import json
import math
import re

from agenti.stage import native, particles

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
    "com e strutturata",
    "com è strutturata",
    "com e strutturato",
    "com è strutturato",
    "com'e strutturata",
    "com'è strutturata",
    "com'e strutturato",
    "com'è strutturato",
    "com e composta",
    "com è composta",
    "com e composto",
    "com è composto",
    "come e composta",
    "come è composta",
    "come e composto",
    "come è composto",
    "come e fatta",
    "come è fatta",
    "come e fatto",
    "come è fatto",
    "com e fatta",
    "com è fatta",
    "com e fatto",
    "com è fatto",
    "com'e fatta",
    "com'è fatta",
    "com'e fatto",
    "com'è fatto",
    "come funziona",
    "anatomia di",
    "struttura di",
    "forma di",
    "mostrami",
    "mi mostri",
    "mi mostra",
    "mi fai vedere",
    "puoi mostrarmi",
    "potresti mostrarmi",
    "mostrarmi",
    "fammi vedere",
    "visualizza",
    "disegnami",
    "rappresentami",
    "fai vedere",
    "fammi un disegno di",
    "che aspetto ha",
    "che aspetto hanno",
    "come appare",
    "come appaiono",
    "voglio vedere",
    "vorrei vedere",
    "draw me",
    "picture of",
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

PALETTES = {
    "bioluminescent": ("#4ce6ff", "#7952ec", "#a87bff", "#ff6be5", "#5ef2ff", "#c49bff"),
    "celestial": ("#ffd166", "#5ce1e6", "#480ca8", "#72efdd", "#9b7bff", "#ff9f1c"),
    "botanical": ("#38b000", "#70e000", "#a7c957", "#ff70a6", "#ffb703", "#007200"),
    "fauna": ("#ee9b00", "#ca6702", "#bb3e03", "#0077b6", "#90e0ef", "#f1faee"),
    "mechanical": ("#64dfdf", "#48bfe3", "#5390d9", "#ff9f1c", "#80ffdb", "#7400b8"),
    "microscopic": ("#ff006e", "#00f5d4", "#8338ec", "#fee440", "#3a86ff", "#ffbe0b"),
    "geological": ("#2ec4b6", "#e71d36", "#ff9f1c", "#7209b7", "#e0aaff", "#c77dff"),
    "ethereal": ("#5ef2ff", "#9b7bff", "#66ffe3", "#ff7be5", "#7aa2ff", "#ffd166"),
}


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


def _color(theme: str, idx: int) -> str:
    palette = PALETTES.get(theme) or PALETTES["ethereal"]
    return palette[idx % len(palette)]


def _generate_radial(theme: str, count: int, is_organism: bool, aspect: float) -> dict:
    core_shape = "sphere" if is_organism else "cylinder"
    sat_shape = "helix" if is_organism else "box"
    parts = [
        _part(core_shape, [1.3 * aspect, 0.85, 1.3 * aspect], [0.0, 0.85, 0.0], [0.0, 0.0, 0.0], _color(theme, 0), 2.4),
        _part("torus", [1.25 * aspect, 0.3, 1.25 * aspect], [0.0, 0.45, 0.0], [0.0, 0.0, 0.0], _color(theme, 1), 1.6),
        _part("cone", [0.45, 1.15, 0.45], [0.0, -0.25, 0.0], [180.0, 0.0, 0.0], _color(theme, 2), 1.4),
    ]
    n = max(4, min(10, count))
    for i in range(n):
        angle = (i / float(n)) * math.tau
        radius = 0.82 * aspect
        x = round(radius * math.cos(angle), 4)
        z = round(radius * math.sin(angle), 4)
        rot_y = float(i * 30) if is_organism else round(-math.degrees(angle), 1)
        parts.append(_part(sat_shape, [0.18, 1.3, 0.18], [x, -0.85, z], [0.0, rot_y, 0.0], _color(theme, i + 3), 1.1))
    return {"parts": parts}


def _generate_bilateral(theme: str, is_vehicle: bool, aspect: float) -> dict:
    spine_shape = "cone" if is_vehicle else "cylinder"
    wing_shape = "box" if is_vehicle else "helix"
    parts = [
        _part(spine_shape, [0.45, 1.6 * aspect, 0.45], [0.0, 0.0, 0.0], [-90.0, 0.0, 0.0], _color(theme, 0), 2.2),
        _part("sphere", [0.55, 0.55, 0.55], [0.0, 0.1, 1.45 * aspect], [0.0, 0.0, 0.0], _color(theme, 1), 1.8),
        _part("cone", [0.35, 0.75, 0.35], [0.0, 0.0, -1.55 * aspect], [90.0, 0.0, 0.0], _color(theme, 2), 1.3),
    ]
    for side in (-1.0, 1.0):
        parts.append(_part(wing_shape, [1.25, 0.12, 0.55], [side * 1.35, 0.05, 0.15], [0.0, side * -18.0, side * 8.0], _color(theme, 3), 1.6))
        parts.append(_part("cone", [0.25, 0.85, 0.25], [side * 0.85, -0.45, -0.5], [-90.0, side * -15.0, 0.0], _color(theme, 4), 1.2))
    return {"parts": parts}


def _generate_orbital(theme: str, count: int) -> dict:
    parts = [_part("sphere", [0.85, 0.85, 0.85], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], _color(theme, 0), 2.6)]
    n = max(2, min(5, count))
    for i in range(n):
        f = i / float(n)
        radius = 1.35 + i * 0.45
        pitch = 25.0 + f * 40.0
        roll = -15.0 + f * 55.0
        parts.append(_part("torus", [radius, 0.18, radius], [0.0, 0.0, 0.0], [pitch, 0.0, roll], _color(theme, i + 1), 1.5))
        theta = f * math.tau + 0.5
        sat_x = round(radius * math.cos(theta) * 0.85, 4)
        sat_y = round(radius * math.sin(theta) * 0.4, 4)
        sat_z = round(radius * math.sin(theta * 1.2) * 0.75, 4)
        parts.append(_part("sphere", [0.22, 0.22, 0.22], [sat_x, sat_y, sat_z], [0.0, 0.0, 0.0], _color(theme, i + 3), 0.9))
    return {"parts": parts}


def _generate_helical(theme: str) -> dict:
    return {
        "parts": [
            _part("sphere", [0.45, 0.45, 0.45], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], _color(theme, 0), 1.8),
            _part("helix", [0.72, 1.85, 0.72], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], _color(theme, 1), 2.2),
            _part("helix", [0.72, 1.85, 0.72], [0.0, 0.0, 0.0], [0.0, 180.0, 0.0], _color(theme, 2), 2.2),
            _part("torus", [1.35, 0.22, 1.35], [0.0, 0.0, 0.0], [32.0, 15.0, 0.0], _color(theme, 3), 1.3),
            _part("torus", [1.35, 0.22, 1.35], [0.0, 0.0, 0.0], [-32.0, -15.0, 0.0], _color(theme, 4), 1.3),
        ]
    }


def _generate_harmonic(theme: str, seed: int, aspect: float) -> dict:
    core_shape = ("sphere", "cylinder", "cone")[seed % 3]
    sat_shape = ("helix", "cone", "cylinder", "sphere")[(seed >> 4) % 4]
    parts = [
        _part(core_shape, [1.05 * aspect, 1.05, 1.05 * aspect], [0.0, 0.15, 0.0], [0.0, 0.0, 0.0], _color(theme, 0), 2.2),
        _part("torus", [1.45 * aspect, 0.28, 1.45 * aspect], [0.0, 0.0, 0.0], [18.0, 0.0, -18.0], _color(theme, 1), 1.7),
        _part("cone", [0.5, 0.9, 0.5], [0.0, 1.15, 0.0], [0.0, 0.0, 0.0], _color(theme, 2), 1.2),
    ]
    for i in range(4):
        angle = (i / 4.0) * math.tau
        radius = 1.15 * aspect
        x = round(radius * math.cos(angle), 4)
        z = round(radius * math.sin(angle), 4)
        parts.append(_part(sat_shape, [0.28, 0.95, 0.28], [x, -0.45, z], [0.0, float(i * 45), 0.0], _color(theme, i + 2), 1.1))
    return {"parts": parts}


def synthesize_spec(concept: str) -> dict:
    if native.lib is not None and hasattr(native.lib, "particles_synthesize_spec"):
        try:
            raw = native.lib.particles_synthesize_spec(str(concept or ""))
            return particles.validate(json.loads(raw))
        except Exception:
            pass
    lower = _clean_text(concept)
    h = 0xCBF29CE484222325
    for b in lower.encode("utf-8"):
        h ^= b
        h = (h * 0x0100000001B3) & 0xFFFFFFFFFFFFFFFF

    if any(k in lower for k in ("medusa", "jellyfish", "polp", "octopus", "squid", "anemon", "cnidar", "starfish")):
        return particles.validate(_generate_radial("bioluminescent", 6, True, 1.35))
    if any(k in lower for k in ("turbin", "propeller", "elica", "rotore", "girandol", "gear", "ruota", "wheel")):
        return particles.validate(_generate_radial("mechanical", 5, False, 0.95))
    if any(k in lower for k in ("aquila", "eagle", "falco", "bird", "farfall", "leone", "pesce", "shark", "ragno", "lupo")):
        return particles.validate(_generate_bilateral("fauna", False, 1.2))
    if any(k in lower for k in ("aereo", "airplane", "jet", "drone", "astronave", "spaceship", "auto", "car", "nave", "ship")):
        return particles.validate(_generate_bilateral("mechanical", True, 1.6))
    if any(k in lower for k in ("atom", "molecol", "nucleo", "planet", "saturn", "galassia", "galaxy", "buco nero", "pulsar")):
        theme = "microscopic" if "atom" in lower or "molecol" in lower else "celestial"
        return particles.validate(_generate_orbital(theme, 3))
    if any(k in lower for k in ("dna", "rna", "spiral", "vortice", "vortex", "ciclone", "tornado")):
        theme = "microscopic" if "dna" in lower or "rna" in lower else "celestial"
        return particles.validate(_generate_helical(theme))
    return particles.validate(_generate_harmonic("ethereal", h, 1.1))


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
