import time
from collections import deque

from agenti.particles import codec as particles, morphogenesis
from agenti.particles.store import concept_key, store as particle_store
from agenti.visual_catalog.catalog import VisualCatalog, catalog as default_catalog

CURATED_ACADEMIC_TOPICS = (
    ("medusa", "particles"),
    ("motore v8", "gaussian_splat"),
    ("Castel dell'Ovo", "diorama"),
    ("cervello umano", "particles"),
    ("atomo", "particles"),
    ("dna", "particles"),
)


class NightDreamSynthesis:
    def __init__(self, target_catalog: VisualCatalog = default_catalog) -> None:
        self.catalog = target_catalog
        self.pending_topics: deque[tuple[str, str]] = deque(CURATED_ACADEMIC_TOPICS)
        self.seen: set[str] = set()
        self.last_synthesized = 0.0

    def observe_topic(self, text: str, preferred_engine: str = "particles") -> str | None:
        concept = morphogenesis.extract_visual_concept(text or "")
        if not concept:
            key = concept_key(text or "")
            if 2 <= len(key) <= 40:
                concept = key
        if not concept:
            return None
        norm = concept.strip().lower()
        if norm not in self.seen:
            self.pending_topics.appendleft((concept, preferred_engine))
        return concept

    def synthesize_one(self, concept: str, engine: str = "particles") -> dict:
        key = concept_key(concept) or "medusa"
        spec = morphogenesis.synthesize_spec(key)
        seed = int.from_bytes(key.encode()[:8].ljust(8, b"\0"), "little")
        blob = particles.sample(spec, 12_000, seed)
        stored = particle_store.put(key, spec, blob)
        hotspots = morphogenesis.extract_hotspots(concept, spec)
        entry = self.catalog.record(
            concept=concept,
            engine=engine,
            digest=stored["digest"],
            spec=spec,
            blob=blob,
            hotspots=hotspots,
        )
        self.seen.add(concept.strip().lower())
        self.last_synthesized = time.time()
        return entry

    def run_idle_cycle(self, max_items: int = 3) -> list[dict]:
        built = []
        limit = max(1, min(12, int(max_items)))
        while self.pending_topics and len(built) < limit:
            concept, engine = self.pending_topics.popleft()
            if self.catalog.lookup(concept) is not None:
                self.seen.add(concept.strip().lower())
                continue
            built.append(self.synthesize_one(concept, engine))
        return built


night_dreamer = NightDreamSynthesis()
