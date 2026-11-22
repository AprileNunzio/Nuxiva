import uuid
import time
import datetime
from typing import Dict, Any, List, Optional, Tuple
from server.features.human_affective_engine.interfaces import (
    MoodState,
    VocalDeliveryMode,
    VoiceAcousticBiomarkers,
    PhysiologicalMultimodalPayload,
    AffectiveInferenceResult,
)

class AffectiveFusionEngine:
    def __init__(self):
        pass

    def infer_affective_state(self, payload: PhysiologicalMultimodalPayload) -> AffectiveInferenceResult:
        hr = payload.heart_metrics
        vox = payload.vocal_metrics
        gaze = payload.ocular_metrics

        dep_score = self._compute_depression_score(hr, vox, gaze)
        anx_score = self._compute_anxiety_score(hr, vox, gaze)
        fatigue_score = self._compute_fatigue_score(hr, vox, gaze)

        mood, confidence = self._classify_dominant_mood(dep_score, anx_score, fatigue_score, vox=vox)
        valence, arousal = self._compute_valence_arousal(dep_score, anx_score, fatigue_score, vox)
        strategy_id, prompt_adapt, tone_guide, ambient_acts = self._generate_intervention(mood, vox)

        now_ts = payload.timestamp
        iso_str = datetime.datetime.fromtimestamp(now_ts, tz=datetime.timezone.utc).isoformat()
        assessment_id = f"aff_{payload.user_id}_{int(now_ts)}_{uuid.uuid4().hex[:6]}"

        return AffectiveInferenceResult(
            assessment_id=assessment_id,
            user_id=payload.user_id,
            timestamp=now_ts,
            iso_timestamp=iso_str,
            detected_mood=mood,
            vocal_delivery_mode=vox.delivery_mode,
            whisper_probability=float(min(1.0, max(0.0, vox.whisper_probability))),
            valence_score=valence,
            arousal_score=arousal,
            depression_risk_score=float(min(1.0, max(0.0, dep_score))),
            anxiety_stress_score=float(min(1.0, max(0.0, anx_score))),
            fatigue_burnout_score=float(min(1.0, max(0.0, fatigue_score))),
            confidence=float(confidence),
            intervention_strategy_id=strategy_id,
            system_prompt_adaptation=prompt_adapt,
            voice_tone_guidance=tone_guide,
            ambient_automation_triggers=ambient_acts
        )

    def infer_from_voice_only(
        self,
        user_id: str,
        vox: VoiceAcousticBiomarkers,
        timestamp: Optional[float] = None,
    ) -> AffectiveInferenceResult:
        """
        Inferenza affettiva e paralinguistica basata esclusivamente sull'audio vocale
        (senza sensori cardiaci o oculari), ideale per interazioni vocali naturali in tempo reale.
        """
        now_ts = timestamp if timestamp is not None else time.time()

        # When whispering, low volume and low voicing are intentional — do not misclassify as depression
        whisper_damp = 1.0 - (0.65 * vox.whisper_probability)
        dep_score = float(min(1.0, max(0.0, vox.depressive_vocal_indicator * whisper_damp)))

        anx_components = 0.0
        if vox.pitch_variability_st > 25.0:
            anx_components += 0.35
        if vox.jitter_percent > 2.2:
            anx_components += 0.30
        if vox.speech_rate_sps > 4.5:
            anx_components += 0.25
        if vox.delivery_mode in (VocalDeliveryMode.TENSE_URGENT, VocalDeliveryMode.SHOUTING):
            anx_components += 0.30
        anx_score = float(min(1.0, max(0.0, anx_components)))

        fatigue_score = float(min(1.0, max(
            0.0,
            (vox.speech_pause_ratio * 0.55)
            + (max(0.0, (2.8 - vox.speech_rate_sps) / 2.8) * 0.30 * whisper_damp)
            + (vox.monotone_score * 0.15 * whisper_damp),
        )))

        mood, confidence = self._classify_dominant_mood(dep_score, anx_score, fatigue_score, vox=vox)
        # Voice-only confidence slightly lower than full multimodal fusion
        confidence = float(min(0.92, max(0.55, confidence * 0.90)))
        valence, arousal = self._compute_valence_arousal(dep_score, anx_score, fatigue_score, vox)
        strategy_id, prompt_adapt, tone_guide, ambient_acts = self._generate_intervention(mood, vox)

        iso_str = datetime.datetime.fromtimestamp(now_ts, tz=datetime.timezone.utc).isoformat()
        assessment_id = f"vox_{user_id}_{int(now_ts)}_{uuid.uuid4().hex[:6]}"

        return AffectiveInferenceResult(
            assessment_id=assessment_id,
            user_id=user_id,
            timestamp=now_ts,
            iso_timestamp=iso_str,
            detected_mood=mood,
            vocal_delivery_mode=vox.delivery_mode,
            whisper_probability=float(min(1.0, max(0.0, vox.whisper_probability))),
            valence_score=valence,
            arousal_score=arousal,
            depression_risk_score=dep_score,
            anxiety_stress_score=anx_score,
            fatigue_burnout_score=fatigue_score,
            confidence=confidence,
            intervention_strategy_id=strategy_id,
            system_prompt_adaptation=prompt_adapt,
            voice_tone_guidance=tone_guide,
            ambient_automation_triggers=ambient_acts,
        )

    def _compute_depression_score(self, hr, vox, gaze) -> float:
        hr_dep = 0.7 if (hr.bpm < 65.0 and hr.hrv_rmssd_ms < 25.0) else 0.2
        vox_dep = vox.depressive_vocal_indicator
        gaze_dep = gaze.blunted_affect_indicator
        return float((hr_dep * 0.25) + (vox_dep * 0.45) + (gaze_dep * 0.30))

    def _compute_anxiety_score(self, hr, vox, gaze) -> float:
        hr_anx = 0.85 if (hr.bpm > 95.0 and hr.hrv_rmssd_ms < 20.0) else 0.15
        vox_anx = 0.8 if (vox.pitch_variability_st > 28.0 or vox.jitter_percent > 2.5) else 0.2
        gaze_anx = 0.75 if (gaze.blink_rate_per_min > 28.0 or gaze.downward_gaze_ratio < 0.05) else 0.2
        return float((hr_anx * 0.45) + (vox_anx * 0.35) + (gaze_anx * 0.20))

    def _compute_fatigue_score(self, hr, vox, gaze) -> float:
        vox_fatigue = vox.speech_pause_ratio
        gaze_fatigue = 1.0 - (gaze.eye_aspect_ratio_mean / 0.35)
        return float((vox_fatigue * 0.45) + (max(0.0, gaze_fatigue) * 0.55))

    def _compute_valence_arousal(
        self,
        dep: float,
        anx: float,
        fatigue: float,
        vox: VoiceAcousticBiomarkers,
    ) -> Tuple[float, float]:
        energy_norm = min(1.0, vox.vocal_energy_rms / 0.30)
        rate_norm = min(1.0, vox.speech_rate_sps / 6.0)
        arousal = float(min(1.0, max(
            0.0,
            (energy_norm * 0.35) + (rate_norm * 0.25) + (anx * 0.40) - (fatigue * 0.25) - (vox.whisper_probability * 0.25),
        )))
        valence = float(min(1.0, max(
            0.0,
            0.65 - (dep * 0.50) - (anx * 0.25) - (fatigue * 0.15)
            + (0.20 if vox.delivery_mode == VocalDeliveryMode.ANIMATED_EXCITED else 0.0),
        )))
        return valence, arousal

    def _classify_dominant_mood(
        self,
        dep: float,
        anx: float,
        fatigue: float,
        vox: Optional[VoiceAcousticBiomarkers] = None,
    ) -> Tuple[MoodState, float]:
        if dep >= 0.65 and dep > anx:
            return MoodState.DEPRESSED_DYSPHORIC, min(0.98, 0.7 + (dep * 0.25))
        if anx >= 0.60:
            return MoodState.ANXIOUS_STRESSED, min(0.98, 0.7 + (anx * 0.25))
        if fatigue >= 0.65:
            return MoodState.FATIGUED_BURNOUT, min(0.95, 0.65 + (fatigue * 0.25))
        if vox is not None and vox.delivery_mode == VocalDeliveryMode.ANIMATED_EXCITED and anx < 0.45 and dep < 0.35:
            return MoodState.EUPHORIC_HIGH_ENERGY, 0.86
        if dep < 0.30 and anx < 0.30 and fatigue < 0.30:
            return MoodState.OPTIMAL_BALANCED, 0.92
        return MoodState.OPTIMAL_BALANCED, 0.85

    def _generate_intervention(
        self,
        mood: MoodState,
        vox: Optional[VoiceAcousticBiomarkers] = None,
    ) -> Tuple[str, str, Dict[str, Any], List[Dict[str, Any]]]:
        if mood == MoodState.DEPRESSED_DYSPHORIC:
            strategy_id = "INTERVENTION_EMPATHIC_WARMTH"
            prompt_adapt = (
                "L'utente presenta marcati indicatori di depressione o umore deflesso. "
                "Rispondi con tono rassicurante, calmo, privo di giudizio. "
                "Riduci il carico cognitivo: risposte concise, suddivise in passi semplici. "
                "Non sollecitare decisioni critiche."
            )
            tone_guide: Dict[str, Any] = {
                "pitch_shift": -1.5,
                "speed": 0.88,
                "warmth_level": "maximum",
                "volume_db": -2.0,
                "whisper_mode": False,
                "tts_style_hint": "empathetic",
            }
            ambient_acts: List[Dict[str, Any]] = [
                {"domain": "light", "action": "set_warm_amber", "brightness": 65},
                {"domain": "media", "action": "suggest_comfort_ambient", "genre": "acoustic_lofi"},
                {"domain": "notification", "action": "suppress_non_urgent", "duration_minutes": 60},
            ]
        elif mood == MoodState.ANXIOUS_STRESSED:
            strategy_id = "INTERVENTION_DE_ESCALATION"
            prompt_adapt = (
                "L'utente presenta tachicardia e marcata ansia/agitazione. "
                "Riduci immediatamente l'ambiguità: fornisci punti fermi e risposte strutturate ad elenco puntato. "
                "Mantieni un tono calmo e autorevole."
            )
            tone_guide = {
                "pitch_shift": -1.0,
                "speed": 0.92,
                "warmth_level": "high",
                "volume_db": -1.0,
                "whisper_mode": False,
                "tts_style_hint": "gentle",
            }
            ambient_acts = [
                {"domain": "light", "action": "set_soft_neutral", "brightness": 50},
                {"domain": "climate", "action": "refresh_ventilation", "target_temp": 20.5},
            ]
        elif mood == MoodState.FATIGUED_BURNOUT:
            strategy_id = "INTERVENTION_FATIGUE_PREVENTION"
            prompt_adapt = (
                "L'utente mostra forte affaticamento e sonnolenza. Sii ultra-sintetico. "
                "Proponi di automatizzare i compiti in background o rimandare il lavoro al giorno successivo."
            )
            tone_guide = {
                "pitch_shift": 0.0,
                "speed": 0.95,
                "warmth_level": "medium",
                "volume_db": 0.0,
                "whisper_mode": False,
                "tts_style_hint": "gentle",
            }
            ambient_acts = [
                {"domain": "display", "action": "enable_night_shift", "blue_filter": True},
            ]
        elif mood == MoodState.EUPHORIC_HIGH_ENERGY:
            strategy_id = "INTERVENTION_ENERGETIC_RESONANCE"
            prompt_adapt = (
                "L'utente mostra entusiasmo ed energia elevata nella voce. "
                "Rispecchia il suo slancio con risposte vivaci, naturali, propositive e spontanee."
            )
            tone_guide = {
                "pitch_shift": 0.5,
                "speed": 1.04,
                "warmth_level": "high",
                "volume_db": 0.5,
                "whisper_mode": False,
                "tts_style_hint": "cheerful",
            }
            ambient_acts = []
        else:
            strategy_id = "INTERVENTION_STANDARD_HIGH_PRODUCTIVITY"
            prompt_adapt = (
                "L'utente è in stato emotivo bilanciato ed energico. "
                "Massima proattività operativa ed efficienza esecutiva."
            )
            tone_guide = {
                "pitch_shift": 0.0,
                "speed": 1.0,
                "warmth_level": "standard",
                "volume_db": 0.0,
                "whisper_mode": False,
                "tts_style_hint": "friendly",
            }
            ambient_acts = []

        # Layer paralinguistic delivery adaptation (whisper, soft intimate, shouting, urgent)
        if vox is not None:
            if vox.delivery_mode == VocalDeliveryMode.WHISPER or vox.whisper_probability >= 0.60:
                if strategy_id == "INTERVENTION_STANDARD_HIGH_PRODUCTIVITY":
                    strategy_id = "INTERVENTION_WHISPER_MIRRORING"
                prompt_adapt = (
                    f"{prompt_adapt} "
                    "L'utente sta sussurrando: abbassa spontaneamente il registro, rispondi in modo "
                    "sommesso, intimo, breve e delicato, rispettando il silenzio o la riservatezza del momento."
                )
                tone_guide["whisper_mode"] = True
                tone_guide["volume_db"] = min(float(tone_guide.get("volume_db", 0.0)), -8.0)
                tone_guide["speed"] = min(float(tone_guide.get("speed", 1.0)), 0.86)
                tone_guide["warmth_level"] = "intimate"
                tone_guide["tts_style_hint"] = "whispering"
            elif vox.delivery_mode == VocalDeliveryMode.SOFT_INTIMATE:
                prompt_adapt = (
                    f"{prompt_adapt} "
                    "L'utente parla a voce molto bassa e raccolta: mantieni un tono dolce, vicino e non invadente."
                )
                tone_guide["volume_db"] = min(float(tone_guide.get("volume_db", 0.0)), -4.5)
                tone_guide["speed"] = min(float(tone_guide.get("speed", 1.0)), 0.92)
                tone_guide["tts_style_hint"] = "gentle"
            elif vox.delivery_mode == VocalDeliveryMode.SHOUTING:
                prompt_adapt = (
                    f"{prompt_adapt} "
                    "L'utente sta parlando a voce molto alta o concitata: non alzare il tono, resta fermo, "
                    "limpido, diretto e distensivo per riportare calma."
                )
                tone_guide["volume_db"] = -1.5
                tone_guide["speed"] = 0.90
                tone_guide["tts_style_hint"] = "gentle"
            elif vox.delivery_mode == VocalDeliveryMode.TENSE_URGENT:
                prompt_adapt = (
                    f"{prompt_adapt} "
                    "L'utente parla con ritmo incalzante e tensione nella voce: vai dritto al punto, "
                    "zero preamboli, risposte chiare e immediatamente utili."
                )
                tone_guide["speed"] = 0.95

        return strategy_id, prompt_adapt, tone_guide, ambient_acts

    def compute_limbic_update(self, payload: PhysiologicalMultimodalPayload) -> Any:
        from server.core.kernel.domain.limbic_state import LimbicState
        res = self.infer_affective_state(payload)
        na = min(1.0, 0.15 + 0.6 * res.anxiety_stress_score)
        c = min(1.0, 0.10 + 0.5 * res.anxiety_stress_score + 0.3 * res.fatigue_burnout_score)
        d = max(0.1, 0.7 - 0.5 * res.depression_risk_score - 0.3 * res.fatigue_burnout_score)
        s = max(0.2, 0.8 - 0.5 * res.anxiety_stress_score)
        return LimbicState(dopamine=d, noradrenaline=na, serotonin=s, cortisol=c, last_update_ts=payload.timestamp)

affective_fusion_engine = AffectiveFusionEngine()
