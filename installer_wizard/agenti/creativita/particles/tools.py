from agenti.particles import codec as particles, morphogenesis
from agenti.particles.store import concept_key, store
from agenti.visual_catalog import catalog


def tool_extract_concept(query: str) -> str:
    found = morphogenesis.extract_visual_concept(query or "")
    if found:
        return found
    return concept_key(query or "") or "medusa"


def tool_synthesize_spec(concept: str) -> dict:
    return morphogenesis.synthesize_spec(concept)


def tool_extract_hotspots(concept: str, spec: dict) -> list[dict]:
    return morphogenesis.extract_hotspots(concept, spec)


def tool_sample_cloud(spec: dict, points: int = 12_000, seed: int = 42) -> bytes:
    return particles.sample(spec, points, seed)


def tool_store_and_index(concept: str, spec: dict, blob: bytes, hotspots: list[dict]) -> dict:
    key = concept_key(concept) or "medusa"
    stored = store.put(key, spec, blob)
    cat_entry = catalog.record(
        concept=concept,
        engine="particles",
        digest=stored["digest"],
        spec=spec,
        blob=blob,
        hotspots=hotspots,
    )
    return {"stored": stored, "catalog_entry": cat_entry}


PARTICLE_AGENT_TOOLS = {
    "extract_concept": tool_extract_concept,
    "synthesize_spec": tool_synthesize_spec,
    "extract_hotspots": tool_extract_hotspots,
    "sample_cloud": tool_sample_cloud,
    "store_and_index": tool_store_and_index,
}
