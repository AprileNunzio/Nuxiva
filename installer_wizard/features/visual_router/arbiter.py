import json

from config import env_get
from features.stage import native

DEFAULT_PRIORITY = "particles,depth_parallax,gaussian_splat,neural_radiance,diorama"

MEMORY_MB = {
    "particles": 4,
    "depth_parallax": 16,
    "diorama": 32,
    "gaussian_splat": 64,
    "neural_radiance": 96,
}

ALIASES = {
    "particles": "particles",
    "particelle": "particles",
    "gaussian_splat": "gaussian_splat",
    "gaussian": "gaussian_splat",
    "3dgs": "gaussian_splat",
    "splat": "gaussian_splat",
    "neural_radiance": "neural_radiance",
    "nerf": "neural_radiance",
    "sdf": "neural_radiance",
    "raymarching": "neural_radiance",
    "realistic": "neural_radiance",
    "depth_parallax": "depth_parallax",
    "depth": "depth_parallax",
    "parallax": "depth_parallax",
    "image_3d": "depth_parallax",
    "png_3d": "depth_parallax",
    "diorama": "diorama",
    "scene_3d": "diorama",
}


def _detect_explicit(query: str) -> str | None:
    lower = str(query or "").lower()
    if any(k in lower for k in ("gaussian", "splatting", "splat", "nuvola gaussiana", "3dgs")):
        return "gaussian_splat"
    if any(k in lower for k in ("nerf", "raymarching", "radiance", "sdf", "fotorealistico", "3d realistico", "luci e ombre", "effetto wow")):
        return "neural_radiance"
    if any(k in lower for k in ("immagine 3d", "foto 3d", "png 3d", "rilievo 3d", "parallasse", "depth map", "da immagine")):
        return "depth_parallax"
    if any(k in lower for k in ("diorama", "plastico 3d", "scena tilt-shift")):
        return "diorama"
    if any(k in lower for k in ("con le particelle", "con delle particelle", "in particelle")):
        return "particles"
    return None


def configured_priority_csv() -> str:
    default_engine = str(env_get("NUXIVA_VISUAL_DEFAULT_ENGINE", "particles") or "particles").strip().lower()
    raw_order = str(env_get("NUXIVA_VISUAL_PRIORITY", DEFAULT_PRIORITY) or DEFAULT_PRIORITY).strip().lower()
    items = [ALIASES[p.strip()] for p in raw_order.split(",") if p.strip() in ALIASES]
    primary = ALIASES.get(default_engine, "particles")
    ordered = [primary] + [item for item in items if item != primary]
    return ",".join(ordered)


def select_visual_engine(
    query: str,
    priority_csv: str | None = None,
    available_memory_mb: int = 512,
) -> dict:
    csv_order = priority_csv if priority_csv is not None else configured_priority_csv()
    mem_mb = max(4, int(available_memory_mb))

    if native.lib is not None and hasattr(native.lib, "visual_route_select"):
        try:
            raw = native.lib.visual_route_select(str(query or ""), str(csv_order), mem_mb)
            return json.loads(raw)
        except Exception:
            pass

    priority = [ALIASES[p.strip()] for p in str(csv_order).split(",") if p.strip() in ALIASES]
    if not priority:
        priority = ["particles", "depth_parallax", "gaussian_splat", "neural_radiance", "diorama"]

    explicit = _detect_explicit(query)
    if explicit:
        return {
            "selected_engine": explicit,
            "reason": f"Richiesta esplicita dell'utente per il motore {explicit}",
            "explicit_override": True,
            "memory_budget_mb": MEMORY_MB[explicit],
            "fallback_order": priority,
        }

    for candidate in priority:
        if MEMORY_MB[candidate] <= mem_mb:
            return {
                "selected_engine": candidate,
                "reason": f"Selezionato da priorità del Cervello ({candidate}) entro budget {mem_mb} MB",
                "explicit_override": False,
                "memory_budget_mb": MEMORY_MB[candidate],
                "fallback_order": priority,
            }

    return {
        "selected_engine": "particles",
        "reason": "Fallback automatico a particelle (consumo minimo di memoria e massima velocità)",
        "explicit_override": False,
        "memory_budget_mb": MEMORY_MB["particles"],
        "fallback_order": priority,
    }


def dispatch_visual_agent(query: str, persist: bool = True) -> dict:
    route = select_visual_engine(query)
    engine = route.get("selected_engine", "particles")
    if engine == "diorama":
        from features.diorama.agent import diorama_agent
        return {"route": route, "artifact": diorama_agent.run(query, persist=persist)}
    if engine == "gaussian_splat":
        from features.gaussian_splat import gaussian_splat_agent
        return {"route": route, "artifact": gaussian_splat_agent.run(query, persist=persist)}
    if engine == "neural_radiance":
        from features.neural_radiance import neural_radiance_agent
        return {"route": route, "artifact": neural_radiance_agent.run(query, persist=persist)}
    if engine == "depth_parallax":
        from features.depth_parallax import depth_parallax_agent
        return {"route": route, "artifact": depth_parallax_agent.run(query, persist=persist)}
    from features.particles import particle_agent
    return {"route": route, "artifact": particle_agent.run(query, persist=persist)}

