from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Optional, Protocol, Sequence

from server.core.core_platform.errors import CortexFailure
from server.core.core_platform.result import Result


class Verdict(str, Enum):
    FAST_PATH = "fast_path"
    GREY_ZONE = "grey_zone"
    SLOW_PATH = "slow_path"


@dataclass(frozen=True, slots=True)
class ArbiterThresholds:
    fast_similarity: float = 0.85
    grey_similarity: float = 0.70
    inhibition_limit: float = 0.60
    fast_weight: float = 0.75
    grey_weight: float = 0.50

    def as_tuple(self) -> tuple[float, float, float, float, float]:
        return (
            self.fast_similarity,
            self.grey_similarity,
            self.inhibition_limit,
            self.fast_weight,
            self.grey_weight,
        )

    def as_dict(self) -> dict[str, float]:
        return {
            "fast_similarity": self.fast_similarity,
            "grey_similarity": self.grey_similarity,
            "inhibition_limit": self.inhibition_limit,
            "fast_weight": self.fast_weight,
            "grey_weight": self.grey_weight,
        }


@dataclass(frozen=True, slots=True)
class RouteOutcome:
    verdict: Verdict
    reason: Optional[str]
    neuron_id: Optional[str]
    positive_similarity: float
    negative_similarity: float
    synaptic_weight: float
    latency_ms: float
    executed: bool = False
    execution_result: Any = None
    degraded: Optional[str] = None

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "reason": self.reason,
            "neuron_id": self.neuron_id,
            "positive_similarity": round(self.positive_similarity, 4),
            "negative_similarity": round(self.negative_similarity, 4),
            "synaptic_weight": round(self.synaptic_weight, 4),
            "latency_ms": round(self.latency_ms, 3),
            "executed": self.executed,
            "degraded": self.degraded,
        }


class EmbeddingEngine(Protocol):
    model_name: str

    def ensure_dimension(self) -> Result[int, CortexFailure]: ...

    def state(self) -> Result[Optional[int], CortexFailure]: ...

    def embed(self, text: str) -> Result[list[float], CortexFailure]: ...


class SlotExtractor(Protocol):
    def extract(self, utterance: str, schema: Sequence[Mapping[str, Any]]) -> Result[dict[str, str], CortexFailure]: ...


class SkillExecutor(Protocol):
    def execute(self, neuron_id: str, slots: Mapping[str, Any]) -> Result[Any, CortexFailure]: ...


class NeuronCatalog(Protocol):
    def slot_schema(self, neuron_id: str) -> Optional[Sequence[Mapping[str, Any]]]: ...
