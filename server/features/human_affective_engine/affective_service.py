import base64
from typing import Dict, Any, Optional
import numpy as np
from server.features.human_affective_engine.interfaces import (
    PhysiologicalMultimodalPayload,
    VoiceAudioAnalysisPayload,
    AffectiveInferenceResult,
)
from server.features.human_affective_engine.affective_fusion_engine import affective_fusion_engine
from server.features.human_affective_engine.adaptive_response_orchestrator import adaptive_response_orchestrator
from server.features.human_affective_engine.vocal_biomarker_extractor import VocalBiomarkerAnalyzer
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
                "delivery_mode": result.vocal_delivery_mode.value,
                "whisper_probability": result.whisper_probability,
                "strategy": result.intervention_strategy_id,
                "confidence": result.confidence,
                "timestamp": result.timestamp
            }
        )
        await sensory_bus.push_observation(obs)
        return result

    async def process_voice_signal(
        self,
        user_id: str,
        pcm_signal: np.ndarray,
        sample_rate: int = 16000,
        timestamp: Optional[float] = None,
    ) -> AffectiveInferenceResult:
        self._total_inferences_performed += 1
        analyzer = VocalBiomarkerAnalyzer(sample_rate=sample_rate)
        vox = analyzer.extract_biomarkers(pcm_signal)
        result = affective_fusion_engine.infer_from_voice_only(user_id, vox, timestamp=timestamp)
        adaptive_response_orchestrator.register_inference(result)

        obs = UniversalObservation(
            modality="affective_voice_paralinguistics",
            source_id=f"user:{user_id}",
            raw_data=result.model_dump(),
            metadata={
                "mood": result.detected_mood.value,
                "delivery_mode": result.vocal_delivery_mode.value,
                "whisper_probability": result.whisper_probability,
                "strategy": result.intervention_strategy_id,
                "confidence": result.confidence,
                "timestamp": result.timestamp,
            },
        )
        await sensory_bus.push_observation(obs)
        return result

    async def process_voice_payload(self, payload: VoiceAudioAnalysisPayload) -> AffectiveInferenceResult:
        if payload.pcm16_b64:
            raw_bytes = base64.b64decode(payload.pcm16_b64)
            signal = np.frombuffer(raw_bytes, dtype="<i2").astype(np.float32) / 32768.0
        elif payload.samples is not None:
            signal = np.asarray(payload.samples, dtype=np.float32)
        else:
            signal = np.zeros(0, dtype=np.float32)
        return await self.process_voice_signal(
            user_id=payload.user_id,
            pcm_signal=signal,
            sample_rate=payload.sample_rate,
            timestamp=payload.timestamp,
        )

    def get_latest_user_affect(self, user_id: str) -> Optional[AffectiveInferenceResult]:
        return adaptive_response_orchestrator.get_latest_affect(user_id)

    def modulate_agent_prompt(self, user_id: str, prompt: str, tts_engine: str = "elevenlabs") -> str:
        return adaptive_response_orchestrator.modulate_system_prompt(user_id, prompt, tts_engine=tts_engine)

    def get_service_metrics(self) -> Dict[str, Any]:
        return {
            "total_inferences_performed": self._total_inferences_performed,
            "engine_status": "ONLINE_ACTIVE"
        }

human_affective_service = HumanAffectiveService()
