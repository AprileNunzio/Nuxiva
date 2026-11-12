from agenti.neural_radiance.engine import synthesize_radiance_scene
from agenti.particles import morphogenesis
from agenti.visual_catalog import catalog


def tool_synthesize_radiance_scene(concept: str) -> dict:
    scene = synthesize_radiance_scene(concept)
    scene["ambient_occlusion_steps"] = 8
    scene["shadow_softness"] = 24.0
    return scene


def tool_record_radiance_scene(concept: str, scene: dict, digest: str = "") -> dict:
    clean_digest = digest or ("d" * 64)
    spec = morphogenesis.synthesize_spec(concept)
    hotspots = morphogenesis.extract_hotspots(concept, spec)
    return catalog.record(
        concept=concept,
        engine="neural_radiance",
        digest=clean_digest,
        spec=spec,
        hotspots=hotspots,
    )


NEURAL_RADIANCE_TOOLS = {
    "synthesize_radiance_scene": tool_synthesize_radiance_scene,
    "record_radiance_scene": tool_record_radiance_scene,
}
