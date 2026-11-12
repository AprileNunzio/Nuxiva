from agenti.depth_parallax.engine import reconstruct_depth_relief
from agenti.depth_parallax.skills import DEPTH_PARALLAX_SKILLS
from agenti.depth_parallax.tools import DEPTH_PARALLAX_TOOLS
from agenti.particles import morphogenesis
from agenti.visual_catalog import catalog, classify_academic_entry


class AutonomousDepthParallaxAgent:
    agent_id = "agent.depth_parallax.v1"
    engine_name = "depth_parallax"

    def __init__(self) -> None:
        self.skills = list(DEPTH_PARALLAX_SKILLS)
        self.tools = dict(DEPTH_PARALLAX_TOOLS)

    def run(
        self,
        concept: str,
        rgba: bytes | None = None,
        width: int = 16,
        height: int = 16,
        digest: str = "",
        persist: bool = True,
    ) -> dict:
        clean_digest = digest or ("e" * 64)
        buf = rgba if rgba is not None else bytes([160, 220, 255, 255] * (width * height))
        scene = reconstruct_depth_relief(concept, buf, width, height, max_vertices=4096)
        spec = morphogenesis.synthesize_spec(concept)
        hotspots = morphogenesis.extract_hotspots(concept, spec)
        cat_entry = (
            catalog.record(concept=concept, engine="depth_parallax", digest=clean_digest, spec=spec, hotspots=hotspots)
            if persist
            else classify_academic_entry(concept, "depth_parallax", clean_digest, hotspots)
        )
        return {
            "agent_id": self.agent_id,
            "concept": str(concept or ""),
            "skill_id": "sobel_bilateral_normal_relief",
            "scene": scene,
            "quality_score": 0.95,
            "catalog_entry": cat_entry,
        }


depth_parallax_agent = AutonomousDepthParallaxAgent()
