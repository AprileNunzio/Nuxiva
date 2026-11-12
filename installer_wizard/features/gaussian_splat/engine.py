import json
import math

from features.particles import morphogenesis
from features.stage import native


def _parse_rgb_norm(hex_color: str) -> list[float]:
    clean = str(hex_color or "").lstrip("#")
    if len(clean) != 6:
        clean = "5ef2ff"
    try:
        return [round(int(clean[i:i + 2], 16) / 255.0, 4) for i in (0, 2, 4)]
    except ValueError:
        return [0.37, 0.95, 1.0]


def synthesize_gaussian_scene(concept: str, subdiv_per_part: int = 12) -> dict:
    subdiv = max(4, min(32, int(subdiv_per_part)))
    if native.lib is not None and hasattr(native.lib, "gaussian_splat_synthesize"):
        try:
            raw = native.lib.gaussian_splat_synthesize(str(concept or ""), subdiv)
            return json.loads(raw)
        except Exception:
            pass

    spec = morphogenesis.synthesize_spec(concept)
    splats = []
    for part in spec.get("parts", []):
        rgb = _parse_rgb_norm(part.get("color", "#5ef2ff"))
        size = part.get("size", [1.0, 1.0, 1.0])
        at = part.get("at", [0.0, 0.0, 0.0])
        shape = part.get("shape", "sphere")
        roughness = 0.18 if shape in ("sphere", "torus") else 0.28
        for idx in range(subdiv):
            t = idx / float(subdiv)
            angle = t * math.tau
            ox = size[0] * 0.45 * math.cos(angle)
            oy = size[1] * (2.0 * t - 1.0) * 0.45
            oz = size[2] * 0.45 * math.sin(angle)
            splats.append({
                "center": [round(at[0] + ox, 4), round(at[1] + oy, 4), round(at[2] + oz, 4)],
                "scale": [round(max(0.04, size[0] * 0.38), 4), round(max(0.04, size[1] * 0.38), 4), round(max(0.04, size[2] * 0.38), 4)],
                "rotation_quat": [1.0, 0.0, 0.0, 0.0],
                "opacity": round(min(0.96, max(0.25, float(part.get("weight", 1.0)) * 0.42)), 4),
                "base_rgb": rgb,
                "sh_directional": [
                    round(rgb[0] * 0.35, 4),
                    round(rgb[1] * 0.35, 4),
                    round(rgb[2] * 0.35, 4),
                    round(0.18 * math.cos(angle), 4),
                    0.22,
                    round(0.18 * math.sin(angle), 4),
                    0.12,
                    0.15,
                    0.24,
                ],
                "roughness": roughness,
            })

    return {
        "concept": str(concept or ""),
        "splats": splats,
        "ambient_light": [0.18, 0.24, 0.34],
        "key_light_dir": [-0.45, 0.78, 0.42],
        "exposure": 1.25,
    }
