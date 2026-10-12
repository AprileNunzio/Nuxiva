import time
from typing import Dict, Any, Optional
from server.features.human_affective_engine.interfaces import (
    PhysiologicalMultimodalPayload,
    AffectiveInferenceResult,
)
from server.features.human_affective_engine.rppg_hemodynamic_extractor import hemodynamic_processor
from server.features.human_affective_engine.vocal_biomarker_extractor import vocal_biomarker_analyzer
from server.features.human_affective_engine.gaze_affect_profiler import gaze_affect_profiler
from server.features.human_affective_engine.affective_fusion_engine import affective_fusion_engine
from server.features.human_affective_engine.adaptive_response_orchestrator import adaptive_response_orchestrator
from server.core.sensory_bus.event_router import sensory_bus
from server.core.event_sourcing.universal_space import UniversalObservation

class HumanAffectiveService:
    def __init__(self):
        self._total_inferences_performed = 0

    async def process_multimodal_assessment(self, payload: PhysiologicalMultimodalPayload) -> AffectiveInferenceResult:
        self._total_inferences_performed += 1
        result = affective_fusion_engine.infer_affective_state(payload)
        adaptive_response_orchestrator.register_inference(result)

        obs = UniversalObservation(
            modality="affective_biometrics",
            source_id=f"user:{payload.user_id}",
            raw_data=result.model_dump(),
            metadata={
                "mood": result.detected_mood.value,
                "strategy": result.intervention_strategy_id,
                "confidence": result.confidence,
                "timestamp": result.timestamp
            }
        )
        await sensory_bus.push_observation(obs)
        return result

    def get_latest_user_affect(self, user_id: str) -> Optional[AffectiveInferenceResult]:
        return adaptive_response_orchestrator.get_latest_affect(user_id)

    def modulate_agent_prompt(self, user_id: str, prompt: str) -> str:
        return adaptive_response_orchestrator.modulate_system_prompt(user_id, prompt)

    def get_service_metrics(self) -> Dict[str, Any]:
        return {
            "total_inferences_performed": self._total_inferences_performed,
            "engine_status": "ONLINE_ACTIVE"
        }

human_affective_service = HumanAffectiveService()
