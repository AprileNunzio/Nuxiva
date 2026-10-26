import math
import time
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Tuple

from server.core.kernel.domain.limbic_state import LimbicState


class NodeKind(str, Enum):
    REASONING = "reasoning"
    CODE = "code"
    TOOL_SYNTHESIS = "tool_synthesis"
    PARAMETRIC = "parametric"
    RPA = "rpa"
    DESTRUCTIVE_IO = "destructive_io"


class RiskLevel(IntEnum):
    READ_ONLY = 0
    REVERSIBLE = 1
    DESTRUCTIVE = 2


class NodeState(str, Enum):
    PENDING = "pending"
    BLOCKED_ON_CONSENSUS = "blocked_on_consensus"
    READY = "ready"
    RUNNING = "running"
    VALIDATING = "validating"
    HEALING = "healing"
    ACCEPTED = "accepted"
    FAILED = "failed"
    SKIPPED = "skipped"
    REJECTED = "rejected"


TERMINAL_STATES = frozenset({NodeState.ACCEPTED, NodeState.FAILED, NodeState.SKIPPED, NodeState.REJECTED})


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    deadline_seconds: float = 300.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1 or self.deadline_seconds <= 0:
            raise ValueError("invalid retry policy")


@dataclass(frozen=True)
class NodeSpec:
    node_id: str
    kind: NodeKind
    description: str
    depends_on: Tuple[str, ...] = ()
    risk: RiskLevel = RiskLevel.READ_ONLY
    validator_id: str = "default"
    intent: str = "GENERAL_INTELLIGENCE"
    retry: RetryPolicy = RetryPolicy()


@dataclass
class SynapticSpike:
    source_neuron: str
    target_cluster: str
    potential: float
    inhibitory_gaba: bool = False
    emotion_vector: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    payload: Any = None
    timestamp: float = field(default_factory=time.time)


class SpikingNeuronNode:
    def __init__(
        self,
        node_id: str,
        threshold: float = 0.85,
        tau_m: float = 0.05,
        rest_potential: float = 0.0,
        reset_potential: float = -0.1,
        refractory_period_s: float = 0.005,
    ) -> None:
        self.node_id = node_id
        self.threshold = threshold
        self.tau_m = max(0.001, tau_m)
        self.rest_potential = rest_potential
        self.reset_potential = reset_potential
        self.refractory_period_s = refractory_period_s
        self.potential = rest_potential
        self.last_spike_ts = 0.0
        self.last_update_ts = time.time()
        self.synaptic_weights: dict[str, float] = {}

    def set_weight(self, source_id: str, weight: float) -> None:
        self.synaptic_weights[source_id] = max(0.0, min(1.0, weight))

    def get_weight(self, source_id: str) -> float:
        return self.synaptic_weights.get(source_id, 0.5)

    def compute_decay(self, now: float) -> float:
        dt = max(0.0, now - self.last_update_ts)
        self.last_update_ts = now
        return math.exp(-dt / self.tau_m)

    async def integrate_and_fire(self, trigger: SynapticSpike, limbic: LimbicState) -> list[SynapticSpike]:
        now = time.time()
        if (now - self.last_spike_ts) < self.refractory_period_s:
            return []

        decay = self.compute_decay(now)
        self.potential = self.rest_potential + (self.potential - self.rest_potential) * decay

        w_ij = self.get_weight(trigger.source_neuron)
        s_j = -1.0 if trigger.inhibitory_gaba else 1.0

        m_limbic = 1.0 + 0.3 * limbic.dopamine - 0.2 * limbic.cortisol
        delta_v = w_ij * s_j * trigger.potential * max(0.1, m_limbic)
        self.potential = max(-1.0, min(2.0, self.potential + delta_v))

        effective_threshold = limbic.modulate_firing_threshold(self.threshold)
        if self.potential >= effective_threshold:
            fired_potential = self.potential
            self.potential = self.reset_potential
            self.last_spike_ts = now
            out_spike = SynapticSpike(
                source_neuron=self.node_id,
                target_cluster=trigger.target_cluster,
                potential=fired_potential,
                inhibitory_gaba=False,
                emotion_vector=limbic.to_vector(),
                payload=trigger.payload,
                timestamp=now,
            )
            return [out_spike]

        return []
