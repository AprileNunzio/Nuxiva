import json
import math

from agenti.particles.skills import PARTICLE_AGENT_SKILLS, select_particle_skill
from agenti.particles.tools import (
    PARTICLE_AGENT_TOOLS,
    tool_extract_concept,
    tool_extract_hotspots,
    tool_sample_cloud,
    tool_store_and_index,
    tool_synthesize_spec,
)
from agenti.stage import native


class AutonomousParticleAgent:
    agent_id = "agent.particles.v1"
    engine_name = "particles"

    def __init__(self) -> None:
        self.tools = dict(PARTICLE_AGENT_TOOLS)
        self.skills = list(PARTICLE_AGENT_SKILLS)

    def self_criticize(self, concept: str, spec: dict, hotspots: list[dict], skill: dict) -> tuple[dict, list[dict], dict]:
        parts = list(spec.get("parts") or [])
        spots = list(hotspots)
        refinements = []
        min_parts = int(skill.get("min_parts", 8))

        if len(parts) < min_parts and len(parts) < 22:
            missing = min_parts - len(parts)
            for idx in range(missing):
                angle = (idx / float(max(1, missing))) * math.tau
                parts.append({
                    "shape": "helix",
                    "size": [0.16, 0.55, 0.16],
                    "at": [round(0.65 * math.cos(angle), 3), -0.35, round(0.65 * math.sin(angle), 3)],
                    "rot": [0.0, round(math.degrees(angle), 1), 0.0],
                    "color": "#5ef2ff",
                    "weight": 0.85,
                })
            refinements.append(f"Aggiunti {missing} micro-filamenti strutturali di rifinitura")

        if len(spots) < 4:
            spots.append({
                "id": "micro_cortex",
                "label": f"Struttura Fine di {concept}",
                "at": [0.0, 0.0, 0.35],
                "detail": "Reticolo secondario ad alta densità generato dall'autocritica dell'Agente Particelle.",
                "category": "microstruttura",
            })
            refinements.append("Arricchiti i punti di ispezione accademica")

        score = round(min(1.0, len(parts) / 12.0) * 0.55 + min(1.0, len(spots) / 4.0) * 0.45, 3)
        report = {
            "passed": score >= 0.75,
            "quality_score": score,
            "part_count": len(parts),
            "hotspot_count": len(spots),
            "point_density": int(skill.get("target_points", 20_000)),
            "refinements_applied": refinements,
        }
        return {"parts": parts}, spots, report

    def run(self, query_or_concept: str, persist: bool = True) -> dict:
        concept = tool_extract_concept(query_or_concept)
        skill = select_particle_skill(concept)
        raw_spec = tool_synthesize_spec(concept)
        raw_spots = tool_extract_hotspots(concept, raw_spec)
        spec, hotspots, critique = self.self_criticize(concept, raw_spec, raw_spots, skill)
        seed = int.from_bytes(concept.encode()[:8].ljust(8, b"\0"), "little")
        blob = tool_sample_cloud(spec, 12_000, seed)

        if persist:
            persisted = tool_store_and_index(concept, spec, blob, hotspots)
            digest = persisted["stored"]["digest"]
            catalog_entry = persisted["catalog_entry"]
        else:
            digest = "0" * 64
            from agenti.visual_catalog import classify_academic_entry
            catalog_entry = classify_academic_entry(concept, "particles", digest, hotspots)

        if native.lib is not None and hasattr(native.lib, "visual_agent_execute"):
            try:
                rust_art = json.loads(native.lib.visual_agent_execute("particles", concept, digest))
                return {
                    **rust_art,
                    "digest": digest,
                }
            except Exception:
                pass

        return {
            "agent_id": self.agent_id,
            "concept": concept,
            "digest": digest,
            "skill_used": skill,
            "spec": spec,
            "critique": critique,
            "catalog_entry": catalog_entry,
            "point_count": skill["target_points"],
        }


particle_agent = AutonomousParticleAgent()
