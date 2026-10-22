import asyncio
import logging
import time
from dataclasses import replace
from typing import Any, Optional, Sequence

from server.core.core_platform.errors import CortexFailure, fail, translate_code
from server.core.core_platform.input_sanitizer import sanitize_utterance
from server.core.core_platform.native_bridge import call_native, load_native
from server.core.core_platform.result import Ok, Result
from server.core.hippocampus_router.contracts import (
    ArbiterThresholds,
    EmbeddingEngine,
    NeuronCatalog,
    RouteOutcome,
    SkillExecutor,
    SlotExtractor,
    Verdict,
)
from server.core.gliner_extractor.slot_validator import validate_slots
from server.core.hippocampus_router.fast_decision_model import FastDecisionModel
from server.core.hippocampus_router.neuron_memory import NeuronMemory
from server.core.hippocampus_router.telemetry import ArbiterTelemetry

logger = logging.getLogger("nuxiva.hippocampus")

INITIAL_SYNAPTIC_WEIGHT = 0.80
MIN_TRAINING_UTTERANCES = 1
MILLISECONDS = 1000.0


class HippocampusService:
    def __init__(
        self,
        embedder: EmbeddingEngine,
        memory: NeuronMemory,
        thresholds: ArbiterThresholds = ArbiterThresholds(),
        extractor: Optional[SlotExtractor] = None,
        executor: Optional[SkillExecutor] = None,
        catalog: Optional[NeuronCatalog] = None,
    ) -> None:
        self._embedder = embedder
        self._memory = memory
        self._model = FastDecisionModel(embedder, memory, thresholds)
        self._extractor = extractor
        self._executor = executor
        self._catalog = catalog
        self._telemetry = ArbiterTelemetry()

    def route(self, utterance: str, lang: Optional[str] = None) -> Result[RouteOutcome, CortexFailure]:
        started = time.perf_counter()
        clean = sanitize_utterance(utterance, lang=lang)
        if not clean.is_ok:
            return clean
        decided = self._model.decide(clean.value)
        if not decided.is_ok:
            return decided
        outcome = decided.value
        if outcome.verdict is Verdict.FAST_PATH:
            outcome = self._execute(clean.value, outcome)
        outcome = replace(outcome, latency_ms=(time.perf_counter() - started) * MILLISECONDS)
        self._telemetry.record(outcome)
        return Ok(outcome)

    async def route_async(self, utterance: str, lang: Optional[str] = None) -> Result[RouteOutcome, CortexFailure]:
        return await asyncio.to_thread(self.route, utterance, lang)

    def _demote(self, outcome: RouteOutcome, degraded: str) -> RouteOutcome:
        return replace(outcome, verdict=Verdict.SLOW_PATH, degraded=degraded)

    def _execute(self, clean: str, outcome: RouteOutcome) -> RouteOutcome:
        schema = self._catalog.slot_schema(outcome.neuron_id) if self._catalog and outcome.neuron_id else None
        if self._extractor is None or self._executor is None or schema is None:
            return self._demote(outcome, "hippocampus.skills.unavailable")
        extracted = self._extractor.extract(clean, schema)
        if not extracted.is_ok:
            return self._demote(outcome, extracted.error.code)
        validated = validate_slots(schema, extracted.value)
        if not validated.is_ok:
            return self._demote(outcome, validated.error.code)
        executed = self._executor.execute(outcome.neuron_id, validated.value)
        if not executed.is_ok:
            return self._demote(outcome, executed.error.code)
        return replace(outcome, executed=True, execution_result=executed.value)

    def learn(self, neuron_id: str, utterances: Sequence[str], weight: float = INITIAL_SYNAPTIC_WEIGHT) -> Result[int, CortexFailure]:
        if len(utterances) < MIN_TRAINING_UTTERANCES:
            return fail("cortex.vector.empty")
        dimension = self._embedder.ensure_dimension()
        if not dimension.is_ok:
            return dimension
        vectors: list[list[float]] = []
        for utterance in utterances:
            clean = sanitize_utterance(utterance)
            if not clean.is_ok:
                return clean
            vector = self._embedder.embed(clean.value)
            if not vector.is_ok:
                return vector
            vectors.append(vector.value)
        index = self._memory.index(dimension.value)
        if not index.is_ok:
            return index
        stored = call_native(lambda _: index.value.upsert(neuron_id, weight, vectors))
        if not stored.is_ok:
            return stored
        persisted = self._memory.persist()
        if not persisted.is_ok:
            logger.warning("Neuron %s learned in memory only (%s)", neuron_id, persisted.error.code)
        return Ok(len(vectors))

    def _live_index(self) -> Result[Any, CortexFailure]:
        dimension = self._embedder.ensure_dimension()
        return dimension if not dimension.is_ok else self._memory.index(dimension.value)

    def _persisted(self, value: Any) -> Result[Any, CortexFailure]:
        saved = self._memory.persist()
        if not saved.is_ok:
            logger.warning("Neuron memory changed in memory only (%s)", saved.error.code)
        return Ok(value)

    def forget(self, neuron_id: str) -> Result[bool, CortexFailure]:
        index = self._live_index()
        if not index.is_ok:
            return index
        removed = call_native(lambda _: index.value.remove(neuron_id))
        return removed if not removed.is_ok else self._persisted(removed.value)

    def weights(self) -> Result[dict[str, float], CortexFailure]:
        index = self._live_index()
        if not index.is_ok:
            return index
        return call_native(lambda _: {nid: index.value.weight(nid) for nid in index.value.neuron_ids()})

    def set_weight(self, neuron_id: str, weight: float) -> Result[float, CortexFailure]:
        index = self._live_index()
        if not index.is_ok:
            return index
        changed = call_native(lambda _: index.value.set_weight(neuron_id, weight))
        return changed if not changed.is_ok else self._persisted(weight)

    def reinforce_with(self, neuron_id: str, utterance: str, inhibit: bool = False) -> Result[None, CortexFailure]:
        clean = sanitize_utterance(utterance)
        if not clean.is_ok:
            return clean
        vector = self._embedder.embed(clean.value)
        if not vector.is_ok:
            return vector
        index = self._live_index()
        if not index.is_ok:
            return index
        action = index.value.add_inhibition if inhibit else index.value.add_dendrite
        stored = call_native(lambda _: action(neuron_id, vector.value))
        return stored if not stored.is_ok else self._persisted(None)

    def status(self, lang: Optional[str] = None) -> dict[str, Any]:
        storage = self._memory.storage_error
        embedding = self._embedder.state()
        loaded = embedding.is_ok and embedding.value is not None
        return {
            "native": self._native_state(lang),
            "embedding": {
                "model": self._embedder.model_name,
                "loaded": loaded,
                "dimension": embedding.value if loaded else None,
                "error": None if embedding.is_ok else self._error(embedding.error, lang),
            },
            "storage": {"persistent": storage is None, "error": self._error(storage, lang)},
            "neurons": self._memory.neuron_count(),
            "thresholds": self._model.thresholds.as_dict(),
            "execution": {
                "extractor": self._extractor is not None,
                "executor": self._executor is not None,
                "catalog": self._catalog is not None,
            },
            "telemetry": self._telemetry.snapshot(),
        }

    def _native_state(self, lang: Optional[str]) -> dict[str, Any]:
        native = load_native()
        return {"available": native.is_ok, "error": None if native.is_ok else self._error(native.error, lang)}

    def _error(self, failure: Optional[CortexFailure], lang: Optional[str]) -> Optional[dict[str, str]]:
        if failure is None:
            return None
        return {"code": failure.code, "message": translate_code(failure.code, lang)}
