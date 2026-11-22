from typing import Optional, Dict, Any
from server.features.human_affective_engine.interfaces import (
    AffectiveInferenceResult,
    MoodState,
    VocalDeliveryMode,
)

class AdaptiveResponseOrchestrator:
    def __init__(self):
        self._current_user_affect: Dict[str, AffectiveInferenceResult] = {}

    def register_inference(self, result: AffectiveInferenceResult) -> None:
        self._current_user_affect[result.user_id] = result

    def clear_user_affect(self, user_id: str) -> None:
        self._current_user_affect.pop(user_id, None)

    def get_latest_affect(self, user_id: str) -> Optional[AffectiveInferenceResult]:
        return self._current_user_affect.get(user_id)

    def modulate_system_prompt(
        self,
        user_id: str,
        base_system_prompt: str,
        tts_engine: str = "elevenlabs",
    ) -> str:
        affect = self._current_user_affect.get(user_id)
        if not affect:
            return base_system_prompt

        is_special_delivery = (
            affect.vocal_delivery_mode != VocalDeliveryMode.CALM_NATURAL
            or affect.whisper_probability >= 0.60
        )
        if affect.detected_mood == MoodState.OPTIMAL_BALANCED and not is_special_delivery:
            return base_system_prompt

        engine_vocal_cue = self._build_engine_vocal_cue(affect, tts_engine)
        delivery_label = affect.vocal_delivery_mode.value.upper()
        whisper_pct = int(round(affect.whisper_probability * 100))

        adaptive_block = (
            f"\n\n[DIRETTIVA ADATTIVA STATO EMOTIVO UTENTE - {affect.detected_mood.value.upper()}]\n"
            f"Modalità vocale rilevata: {delivery_label} "
            f"(probabilità sussurro: {whisper_pct}%, arousal: {affect.arousal_score:.2f}, valenza: {affect.valence_score:.2f})\n"
            f"{affect.system_prompt_adaptation}\n"
            f"{engine_vocal_cue}"
            "Regola di naturalezza umana: NON usare frasi preconfezionate o formule ripetitive e NON annunciare "
            "meccanicamente di aver rilevato il tono o il sussurro; adatta invece spontaneamente lessico, "
            "lunghezza delle frasi, ritmo ed empatia come farebbe una persona reale presente nella stanza.\n"
            f"Parametri Vocali Suggeriti: {affect.voice_tone_guidance}"
        )
        return f"{base_system_prompt}{adaptive_block}"

    def _build_engine_vocal_cue(self, affect: AffectiveInferenceResult, tts_engine: str) -> str:
        engine = (tts_engine or "elevenlabs").lower().strip()
        is_whisper = (
            affect.vocal_delivery_mode == VocalDeliveryMode.WHISPER
            or affect.whisper_probability >= 0.60
            or bool(affect.voice_tone_guidance.get("whisper_mode"))
        )
        if is_whisper:
            if engine == "elevenlabs":
                return (
                    "Guida espressiva TTS (ElevenLabs): usa in modo naturale [whispering] o [softly] "
                    "all'inizio o nei passaggi più intimi della risposta, con frasi brevi e delicate.\n"
                )
            if engine == "azure":
                return (
                    "Guida espressiva TTS (Azure SSML): avvolgi la risposta o le parti più raccolte con "
                    "<style:whispering>...</style:whispering> e pause morbide come <pause:250ms/>.\n"
                )
            return (
                f"Guida espressiva TTS ({engine}): NON inserire MAI tag tra parentesi quadre; "
                "trasmetti il sussurro e la delicatezza solo tramite parole morbide, frasi brevi e pause (...).\n"
            )

        if affect.vocal_delivery_mode == VocalDeliveryMode.SOFT_INTIMATE:
            if engine == "elevenlabs":
                return "Guida espressiva TTS (ElevenLabs): preferisci un registro caldo e raccolto con [softly] se opportuno.\n"
            if engine == "azure":
                return "Guida espressiva TTS (Azure SSML): usa <style:gentle>...</style:gentle> per mantenere morbidezza.\n"
            return "Guida espressiva TTS: mantieni un ritmo disteso, intimo e non invadente.\n"

        if affect.detected_mood == MoodState.DEPRESSED_DYSPHORIC and engine == "azure":
            return "Guida espressiva TTS (Azure SSML): usa <style:empathetic>...</style:empathetic>.\n"

        return ""

    def get_voice_modulation_params(self, user_id: str) -> Dict[str, Any]:
        affect = self._current_user_affect.get(user_id)
        if not affect:
            return {
                "pitch_shift": 0.0,
                "speed": 1.0,
                "warmth_level": "standard",
                "volume_db": 0.0,
                "whisper_mode": False,
                "tts_style_hint": "friendly",
            }
        return dict(affect.voice_tone_guidance)

    def get_recommended_temperature(self, user_id: str, default: float = 0.55) -> float:
        affect = self._current_user_affect.get(user_id)
        if not affect:
            return default
        if affect.detected_mood == MoodState.ANXIOUS_STRESSED or affect.vocal_delivery_mode in (
            VocalDeliveryMode.TENSE_URGENT,
            VocalDeliveryMode.SHOUTING,
        ):
            return 0.30
        if affect.vocal_delivery_mode in (VocalDeliveryMode.WHISPER, VocalDeliveryMode.SOFT_INTIMATE):
            return 0.65
        if affect.detected_mood == MoodState.EUPHORIC_HIGH_ENERGY:
            return 0.72
        return default

adaptive_response_orchestrator = AdaptiveResponseOrchestrator()
