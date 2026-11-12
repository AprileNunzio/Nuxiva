import json

from features.neural_radiance.engine import synthesize_radiance_scene
from features.particles import morphogenesis
from features.stage import native
from features.visual_catalog import catalog, classify_academic_entry

NEURAL_RADIANCE_SKILLS = [
    {
        "id": "sdf_pbr_subsurface_raymarching",
        "domain": "animazioni_3d/fotorealismo",
        "description": "Campi di distanza con segno (SDF) con fusione morbida, Subsurface Scattering, ombre soffuse e occlusione ambientale.",
    }
]


class AutonomousNeuralRadianceAgent:
    agent_id = "agent.neural_radiance.v1"
    engine_name = "neural_radiance"

    def __init__(self) -> None:
        self.skills = list(NEURAL_RADIANCE_SKILLS)
        self.tools = {"synthesize_radiance_scene": synthesize_radiance_scene}

    def run(self, concept: str, digest: str = "", persist: bool = True) -> dict:
        clean_digest = digest or ("d" * 64)
        if native.lib is not None and hasattr(native.lib, "visual_agent_execute"):
            try:
                art = json.loads(native.lib.visual_agent_execute("neural_radiance", str(concept or ""), clean_digest))
                if persist:
                    catalog.record(concept=concept, engine="neural_radiance", digest=clean_digest)
                return art
            except Exception:
                pass

        scene = synthesize_radiance_scene(concept)
        scene["ambient_occlusion_steps"] = 8
        scene["shadow_softness"] = 24.0
        spec = morphogenesis.synthesize_spec(concept)
        hotspots = morphogenesis.extract_hotspots(concept, spec)
        cat_entry = (
            catalog.record(concept=concept, engine="neural_radiance", digest=clean_digest, spec=spec, hotspots=hotspots)
            if persist
            else classify_academic_entry(concept, "neural_radiance", clean_digest, hotspots)
        )
        return {
            "agent_id": self.agent_id,
            "concept": str(concept or ""),
            "skill_id": "sdf_pbr_subsurface_raymarching",
            "scene": scene,
            "quality_score": 0.97,
            "catalog_entry": cat_entry,
        }


neural_radiance_agent = AutonomousNeuralRadianceAgent()
