import asyncio
from dataclasses import dataclass
from typing import Any, Optional
from server.features.llm_gateway.contracts import CognitiveEngineVersion

@dataclass
class LatentSpikePacket:
    source_neuron_id: int
    target_cluster_id: int
    dlpack_hidden_state: Any
    potential: float
    inhibitory_gaba: bool
    surprise_error: float

@dataclass
class CognitiveExecutionResult:
    active_engine: CognitiveEngineVersion
    latent_state: Any
    complexity_psi: float
    limbic_vector: Any
    latency_ms: float
    success: bool

class OmniCorticalEngine:
    def __init__(
        self,
        rust_bus: Any = None,
        limbic_matrix: Any = None,
        twin_simulator: Any = None,
        prm_critic: Any = None,
    ) -> None:
        self.bus = rust_bus
        self.limbic = limbic_matrix
        self.twin = twin_simulator
        self.critic = prm_critic
        self.active_version = CognitiveEngineVersion.AUTO_6_5
        self.fallback_version = CognitiveEngineVersion.EMPATICO_5_0
        self.previous_snapshot: Optional[Any] = None

    def select_active_engine(
        self,
        requested: CognitiveEngineVersion,
        complexity_psi: float,
        user_emotion: float = 0.0,
    ) -> CognitiveEngineVersion:
        if requested != CognitiveEngineVersion.AUTO_6_5:
            return requested
        if complexity_psi < 0.25:
            return CognitiveEngineVersion.VELOCE_5_0
        if complexity_psi < 0.50 or user_emotion > 0.70:
            return CognitiveEngineVersion.EMPATICO_5_0
        if complexity_psi < 0.75:
            return CognitiveEngineVersion.PRO_6_0
        return CognitiveEngineVersion.ULTRA_6_5

    def set_active_version(self, version: CognitiveEngineVersion) -> CognitiveEngineVersion:
        self.active_version = version
        return self.active_version

    async def execute_cognitive_cycle(
        self,
        sensory_tensor: Any,
        requested_ver: Optional[CognitiveEngineVersion] = None,
        user_emotion: float = 0.0,
    ) -> CognitiveExecutionResult:
        version_to_use = requested_ver or self.active_version
        start_time = asyncio.get_event_loop().time()
        
        limbic_vec = None
        if self.limbic is not None:
            if hasattr(self.limbic, "compute_steering_tensor"):
                limbic_vec = await self.limbic.compute_steering_tensor()
            elif hasattr(self.limbic, "get_vector"):
                limbic_vec = self.limbic.get_vector()

        steered_state = sensory_tensor
        psi = 0.15
        if self.bus is not None:
            if hasattr(self.bus, "apply_limbic_addition_cuda") and limbic_vec is not None:
                steered_state = self.bus.apply_limbic_addition_cuda(sensory_tensor, limbic_vec)
            if hasattr(self.bus, "compute_free_energy_surprise"):
                psi = float(self.bus.compute_free_energy_surprise(steered_state))

        selected_engine = self.select_active_engine(version_to_use, psi, user_emotion)

        if selected_engine == CognitiveEngineVersion.ULTRA_6_5 and self.critic is not None:
            if hasattr(self.critic, "evaluate_latent_pathways"):
                steered_state = await self.critic.evaluate_latent_pathways(steered_state)

        elapsed_ms = (asyncio.get_event_loop().time() - start_time) * 1000.0

        return CognitiveExecutionResult(
            active_engine=selected_engine,
            latent_state=steered_state,
            complexity_psi=psi,
            limbic_vector=limbic_vec,
            latency_ms=elapsed_ms,
            success=True,
        )

    def recover_from_anomaly(self) -> CognitiveEngineVersion:
        self.active_version = self.fallback_version
        return self.active_version
