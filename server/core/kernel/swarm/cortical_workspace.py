import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from server.core.kernel.domain.limbic_state import LimbicState
from server.core.kernel.domain.node import SpikingNeuronNode, SynapticSpike


@dataclass
class ThoughtOutcome:
    winning_spikes: list[SynapticSpike] = field(default_factory=list)
    ignited: bool = False
    selected_thought: Any = None
    limbic_vector: list[float] = field(default_factory=list)
    elapsed_ms: float = 0.0
    consensus_passed: bool = True
    active_lanes_count: int = 0


class CorticalGlobalWorkspace:
    def __init__(self, synaptic_bus: Any, limbic: LimbicState, jury: Any = None) -> None:
        self.bus = synaptic_bus
        self.limbic = limbic
        self.jury = jury
        self.neurons: dict[str, SpikingNeuronNode] = {}
        self.ignition_threshold: float = 0.85
        self._init_standard_cortical_populations()

    def _init_standard_cortical_populations(self) -> None:
        populations = [
            ("sensory_talamus", 0.75),
            ("memory_recall", 0.80),
            ("tool_matching", 0.82),
            ("affective_analysis", 0.78),
            ("logic_dag", 0.85),
            ("theory_of_mind", 0.80),
            ("episodic_stdp", 0.82),
            ("executive_synthesis", 0.85),
        ]
        for name, th in populations:
            self.neurons[name] = SpikingNeuronNode(node_id=name, threshold=th)

    def pre_activate_sublexical(self, candidate_neurons: list[str]) -> None:
        for name in candidate_neurons:
            neuron = self.neurons.get(name)
            if neuron:
                effective_th = self.limbic.modulate_firing_threshold(neuron.threshold)
                neuron.potential = max(neuron.potential, 0.7 * effective_th)

    def _inhibit_competing_tasks(self, active_tasks: set[asyncio.Task], min_potential: float) -> None:
        to_cancel = [t for t in active_tasks if getattr(t, "_potential", 0.0) < min_potential and not t.done()]
        for task in to_cancel:
            task.cancel()

    async def process_sensory_wave(self, spikes: list[SynapticSpike], timeout_s: float = 0.18) -> ThoughtOutcome:
        start_time = time.time()
        self.limbic.apply_homeostatic_decay(start_time)
        ignition_event = asyncio.Event()
        winning_coalition: list[SynapticSpike] = []
        active_tasks: set[asyncio.Task] = set()

        effective_lanes = self.limbic.modulate_parallel_lanes(4)

        async def fire_neuron_branch(neuron: SpikingNeuronNode, trigger: SynapticSpike) -> None:
            try:
                out_spikes = await neuron.integrate_and_fire(trigger, self.limbic)
                for out in out_spikes:
                    if out.inhibitory_gaba:
                        self._inhibit_competing_tasks(active_tasks, min_potential=out.potential)
                    if out.potential >= self.limbic.modulate_ignition(self.ignition_threshold):
                        winning_coalition.append(out)
                        ignition_event.set()
                        return
            except asyncio.CancelledError:
                pass

        for spike in spikes[:effective_lanes]:
            target = spike.target_cluster or "logic_dag"
            neuron = self.neurons.get(target)
            if not neuron:
                neuron = SpikingNeuronNode(node_id=target)
                self.neurons[target] = neuron
            task = asyncio.create_task(fire_neuron_branch(neuron, spike))
            setattr(task, "_potential", spike.potential)
            active_tasks.add(task)

        if not active_tasks:
            return ThoughtOutcome(
                winning_spikes=[],
                ignited=False,
                limbic_vector=self.limbic.to_vector(),
                elapsed_ms=(time.time() - start_time) * 1000.0,
                active_lanes_count=0,
            )

        window_s = min(timeout_s, self.limbic.coalescence_window_s())
        try:
            await asyncio.wait_for(ignition_event.wait(), timeout=window_s)
        except (asyncio.TimeoutError, TimeoutError):
            pass

        for task in active_tasks:
            if not task.done():
                task.cancel()

        consensus_ok = True
        if self.limbic.requires_critical_consensus() and self.jury is not None:
            validate_fn = getattr(self.jury, "validate_coalition", None)
            if callable(validate_fn):
                try:
                    consensus_ok = bool(await validate_fn(winning_coalition))
                except Exception:
                    consensus_ok = False

        elapsed = (time.time() - start_time) * 1000.0
        best_thought = winning_coalition[0].payload if winning_coalition else None

        return ThoughtOutcome(
            winning_spikes=winning_coalition,
            ignited=bool(winning_coalition),
            selected_thought=best_thought,
            limbic_vector=self.limbic.to_vector(),
            elapsed_ms=elapsed,
            consensus_passed=consensus_ok,
            active_lanes_count=len(active_tasks),
        )
