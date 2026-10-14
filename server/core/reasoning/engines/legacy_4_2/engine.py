from typing import Any, Dict, List, Optional
from server.core.reasoning.engines.base import BaseReasoningEngine
from server.features.llm_gateway.contracts import CognitiveEngineVersion

class LegacyChainSyncEngine(BaseReasoningEngine):
    @property
    def version(self) -> CognitiveEngineVersion:
        return CognitiveEngineVersion.LEGACY_4_2

    @property
    def name(self) -> str:
        return "Nuxiva 4.2 Legacy Chain-Sync"

    @property
    def architecture(self) -> str:
        return "Sequential Python Pipeline (brain_chain.py)"

    @property
    def latency_sla_ms(self) -> int:
        return 2500

    @property
    def icon(self) -> str:
        return "💾"

    @property
    def vram_mb(self) -> int:
        return 512

    def get_flow_stages(self, query: str = "", context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return [
            {
                "kind": "reasoning",
                "name": "Nuxiva 4.2 Legacy · Pipeline Sequenziale Token",
                "detail": "Generazione token-by-token sequenziale sincrona mono-corsia con memoria tampone standard (architettura Nuxiva 4.2).",
                "label": "sequenziale",
            },
            {
                "kind": "decision",
                "name": "Verifica Deterministica di Fallback",
                "detail": "Controllo di coerenza grammaticale e chiusura dello stream seriale di riserva.",
                "label": "fallback",
            },
        ]

    async def process_latent_state(
        self,
        sensory_tensor: Any,
        limbic_vector: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        return sensory_tensor

