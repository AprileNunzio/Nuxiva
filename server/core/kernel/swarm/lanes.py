import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from typing import AsyncIterator, Dict, Tuple

from server.core.kernel.domain.node import NodeKind


class Lane(str, Enum):
    ANALYTIC = "analytic"
    CODING = "coding"
    PARAMETRIC = "parametric"
    ACTUATION = "actuation"
    SYNTHESIS = "synthesis"
    THEORY_OF_MIND = "theory_of_mind"
    AFFECTIVE = "affective"
    EPISODIC_MEMORY = "episodic_memory"


@dataclass(frozen=True)
class LaneSpec:
    lane: Lane
    agent_ids: Tuple[str, ...]
    concurrency: int


LANES: Tuple[LaneSpec, ...] = (
    LaneSpec(Lane.ANALYTIC, ("analytic_reasoner",), 4),
    LaneSpec(Lane.CODING, ("agent_self_healing_coder",), 2),
    LaneSpec(Lane.SYNTHESIS, ("tool_builder", "skill_synthesizer"), 2),
    LaneSpec(Lane.PARAMETRIC, ("parametric_designer", "genera_modello_3d"), 2),
    LaneSpec(Lane.ACTUATION, ("sysops_agent", "domotics"), 2),
    LaneSpec(Lane.THEORY_OF_MIND, ("psychological_agent",), 2),
    LaneSpec(Lane.AFFECTIVE, ("affective_fusion_engine",), 2),
    LaneSpec(Lane.EPISODIC_MEMORY, ("deep_memory",), 2),
)

LANE_BY_KIND: Dict[NodeKind, Lane] = {
    NodeKind.REASONING: Lane.ANALYTIC,
    NodeKind.CODE: Lane.CODING,
    NodeKind.TOOL_SYNTHESIS: Lane.SYNTHESIS,
    NodeKind.PARAMETRIC: Lane.PARAMETRIC,
    NodeKind.RPA: Lane.ACTUATION,
    NodeKind.DESTRUCTIVE_IO: Lane.ACTUATION,
}


def lane_for(kind: NodeKind) -> Lane:
    return LANE_BY_KIND.get(kind, Lane.ANALYTIC)


class LaneGovernor:
    def __init__(self, specs: Tuple[LaneSpec, ...] = LANES) -> None:
        self._specs: Dict[Lane, LaneSpec] = {s.lane: s for s in specs}
        self._slots: Dict[Lane, asyncio.Semaphore] = {s.lane: asyncio.Semaphore(s.concurrency) for s in specs}

    def spec(self, lane: Lane) -> LaneSpec:
        return self._specs[lane]

    @asynccontextmanager
    async def slot(self, lane: Lane) -> AsyncIterator[None]:
        async with self._slots[lane]:
            yield
