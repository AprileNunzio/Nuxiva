import json

from features.particles import morphogenesis
from features.stage import native

SDF_PRIMITIVES = {
    "sphere": "sdSphere",
    "box": "sdRoundBox",
    "cylinder": "sdCappedCylinder",
    "cone": "sdRoundCone",
    "torus": "sdTorus",
    "helix": "sdSpiralCapsule",
    "plane": "sdPlane",
}


def _hex_to_rgb(hex_color: str) -> list[float]:
    clean = str(hex_color or "").lstrip("#")
    if len(clean) != 6:
        clean = "5ef2ff"
    try:
        return [round(int(clean[i:i + 2], 16) / 255.0, 4) for i in (0, 2, 4)]
    except ValueError:
        return [0.37, 0.95, 1.0]


def synthesize_radiance_scene(concept: str) -> dict:
    if native.lib is not None and hasattr(native.lib, "neural_radiance_synthesize"):
        try:
            raw = native.lib.neural_radiance_synthesize(str(concept or ""))
            return json.loads(raw)
        except Exception:
            pass

    lower = str(concept or "").lower()
    is_organic = not any(
        kw in lower
        for kw in ("motore", "turbina", "drone", "razzo", "aereo", "auto", "macchina", "robot", "torre")
    )
    spec = morphogenesis.synthesize_spec(concept)
    nodes = []
    for part in spec.get("parts", []):
        shape = str(part.get("shape", "sphere")).lower()
        nodes.append({
            "primitive": SDF_PRIMITIVES.get(shape, "sdSphere"),
            "center": list(part.get("at", [0.0, 0.0, 0.0])),
            "extents": list(part.get("size", [1.0, 1.0, 1.0])),
            "rotation_deg": list(part.get("rot", [0.0, 0.0, 0.0])),
            "albedo_rgb": _hex_to_rgb(part.get("color", "#5ef2ff")),
            "metallic": 0.08 if is_organic else 0.72,
            "roughness": 0.24 if is_organic else 0.18,
            "subsurface": 0.68 if is_organic else 0.05,
            "emission": 0.32 if is_organic else 0.14,
            "blend_k": 0.28 if is_organic else 0.06,
        })

    return {
        "concept": str(concept or ""),
        "nodes": nodes,
        "smooth_union_k": 0.25 if is_organic else 0.05,
        "key_light": [-0.55, 0.75, 0.45],
        "fill_light": [0.65, 0.25, 0.40],
        "rim_light": [0.0, 0.45, -0.88],
        "ambient_occlusion_steps": 6,
        "shadow_softness": 16.0,
    }
