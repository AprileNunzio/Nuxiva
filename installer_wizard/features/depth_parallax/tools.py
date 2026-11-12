from features.depth_parallax.engine import reconstruct_depth_relief
from features.particles import morphogenesis
from features.visual_catalog import catalog


def tool_reconstruct_depth_relief(
    concept: str,
    rgba: bytes,
    width: int = 16,
    height: int = 16,
    max_vertices: int = 4096,
) -> dict:
    return reconstruct_depth_relief(concept, rgba, width, height, max_vertices)


def tool_record_depth_relief(concept: str, scene: dict, digest: str = "") -> dict:
    clean_digest = digest or ("e" * 64)
    spec = morphogenesis.synthesize_spec(concept)
    hotspots = morphogenesis.extract_hotspots(concept, spec)
    return catalog.record(
        concept=concept,
        engine="depth_parallax",
        digest=clean_digest,
        spec=spec,
        hotspots=hotspots,
    )


DEPTH_PARALLAX_TOOLS = {
    "reconstruct_depth_relief": tool_reconstruct_depth_relief,
    "record_depth_relief": tool_record_depth_relief,
}
