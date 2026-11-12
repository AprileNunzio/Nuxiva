from agenti.gaussian_splat.engine import synthesize_gaussian_scene
from agenti.particles import morphogenesis
from agenti.visual_catalog import catalog


def tool_synthesize_gaussian_scene(concept: str, subdiv_per_part: int = 16) -> dict:
    return synthesize_gaussian_scene(concept, subdiv_per_part)


def tool_record_gaussian_scene(concept: str, scene: dict, digest: str = "") -> dict:
    clean_digest = digest or ("b" * 64)
    spec = morphogenesis.synthesize_spec(concept)
    hotspots = morphogenesis.extract_hotspots(concept, spec)
    return catalog.record(
        concept=concept,
        engine="gaussian_splat",
        digest=clean_digest,
        spec=spec,
        hotspots=hotspots,
    )


GAUSSIAN_AGENT_TOOLS = {
    "synthesize_gaussian_scene": tool_synthesize_gaussian_scene,
    "record_gaussian_scene": tool_record_gaussian_scene,
}
