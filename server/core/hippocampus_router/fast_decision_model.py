import time
from server.core.core_platform.errors import CortexFailure
from server.core.core_platform.native_bridge import call_native
from server.core.core_platform.result import Result
from server.core.hippocampus_router.contracts import ArbiterThresholds, EmbeddingEngine, RouteOutcome, Verdict
from server.core.hippocampus_router.neuron_memory import NeuronMemory

MILLISECONDS = 1000.0


def _outcome(row: tuple, started: float) -> RouteOutcome:
    verdict, reason, neuron_id, positive, negative, weight = row
    return RouteOutcome(
        verdict=Verdict(verdict),
        reason=reason,
        neuron_id=neuron_id,
        positive_similarity=positive,
        negative_similarity=negative,
        synaptic_weight=weight,
        latency_ms=(time.perf_counter() - started) * MILLISECONDS,
    )


class FastDecisionModel:
    def __init__(self, embedder: EmbeddingEngine, memory: NeuronMemory, thresholds: ArbiterThresholds) -> None:
        self._embedder = embedder
        self._memory = memory
        self._thresholds = thresholds

    @property
    def thresholds(self) -> ArbiterThresholds:
        return self._thresholds

    def decide(self, clean_utterance: str) -> Result[RouteOutcome, CortexFailure]:
        started = time.perf_counter()
        dimension = self._embedder.ensure_dimension()
        if not dimension.is_ok:
            return dimension
        index = self._memory.index(dimension.value)
        if not index.is_ok:
            return index
        vector = self._embedder.embed(clean_utterance)
        if not vector.is_ok:
            return vector
        row = call_native(lambda _: index.value.route(vector.value, self._thresholds.as_tuple()))
        return row.map(lambda value: _outcome(value, started)) if row.is_ok else row
