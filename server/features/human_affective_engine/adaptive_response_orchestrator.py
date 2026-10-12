from typing import Optional, Dict, Any
from server.features.human_affective_engine.interfaces import AffectiveInferenceResult, MoodState

class AdaptiveResponseOrchestrator:
    def __init__(self):
        self._current_user_affect: Dict[str, AffectiveInferenceResult] = {}

    def register_inference(self, result: AffectiveInferenceResult) -> None:
        self._current_user_affect[result.user_id] = result

    def get_latest_affect(self, user_id: str) -> Optional[AffectiveInferenceResult]:
        return self._current_user_affect.get(user_id)

    def modulate_system_prompt(self, user_id: str, base_system_prompt: str) -> str:
        affect = self._current_user_affect.get(user_id)
        if not affect or affect.detected_mood == MoodState.OPTIMAL_BALANCED:
            return base_system_prompt

        adaptive_block = (
            f"\n\n[DIRETTIVA ADATTIVA STATO EMOTIVO UTENTE - {affect.detected_mood.value.upper()}]\n"
            f"{affect.system_prompt_adaptation}\n"
            f"Parametri Vocali Suggeriti: {affect.voice_tone_guidance}"
        )
        return f"{base_system_prompt}{adaptive_block}"

    def get_voice_modulation_params(self, user_id: str) -> Dict[str, Any]:
        affect = self._current_user_affect.get(user_id)
        if not affect:
            return {"pitch_shift": 0.0, "speed": 1.0, "warmth_level": "standard", "volume_db": 0.0}
        return affect.voice_tone_guidance

adaptive_response_orchestrator = AdaptiveResponseOrchestrator()
