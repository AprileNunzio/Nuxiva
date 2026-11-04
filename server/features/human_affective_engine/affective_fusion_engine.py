import uuid
import datetime
from typing import Dict, Any, List, Tuple
from server.features.human_affective_engine.interfaces import (
    MoodState,
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

        mood, confidence = self._classify_dominant_mood(dep_score, anx_score, fatigue_score)
        strategy_id, prompt_adapt, tone_guide, ambient_acts = self._generate_intervention(mood)

        now_ts = payload.timestamp
        iso_str = datetime.datetime.fromtimestamp(now_ts, tz=datetime.timezone.utc).isoformat()
        assessment_id = f"aff_{payload.user_id}_{int(now_ts)}_{uuid.uuid4().hex[:6]}"

        return AffectiveInferenceResult(
            assessment_id=assessment_id,
            user_id=payload.user_id,
            timestamp=now_ts,
            iso_timestamp=iso_str,
            detected_mood=mood,
            depression_risk_score=float(min(1.0, max(0.0, dep_score))),
            anxiety_stress_score=float(min(1.0, max(0.0, anx_score))),
            fatigue_burnout_score=float(min(1.0, max(0.0, fatigue_score))),
            confidence=float(confidence),
            intervention_strategy_id=strategy_id,
            system_prompt_adaptation=prompt_adapt,
            voice_tone_guidance=tone_guide,
            ambient_automation_triggers=ambient_acts
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

    def _classify_dominant_mood(self, dep: float, anx: float, fatigue: float) -> Tuple[MoodState, float]:
        if dep >= 0.65 and dep > anx:
            return MoodState.DEPRESSED_DYSPHORIC, min(0.98, 0.7 + (dep * 0.25))
        if anx >= 0.60:
            return MoodState.ANXIOUS_STRESSED, min(0.98, 0.7 + (anx * 0.25))
        if fatigue >= 0.65:
            return MoodState.FATIGUED_BURNOUT, min(0.95, 0.65 + (fatigue * 0.25))
        if dep < 0.30 and anx < 0.30 and fatigue < 0.30:
            return MoodState.OPTIMAL_BALANCED, 0.92
        return MoodState.OPTIMAL_BALANCED, 0.85

    def _generate_intervention(self, mood: MoodState) -> Tuple[str, str, Dict[str, Any], List[Dict[str, Any]]]:
        if mood == MoodState.DEPRESSED_DYSPHORIC:
            return (
                "INTERVENTION_EMPATHIC_WARMTH",
                "L'utente presenta marcati indicatori di depressione o umore deflesso. Rispondi con tono rassicurante, calmo, privo di giudizio. Riduci il carico cognitivo: risposte concise, suddivise in passi semplici. Non sollecitare decisioni critiche.",
                {"pitch_shift": -1.5, "speed": 0.88, "warmth_level": "maximum", "volume_db": -2.0},
                [
                    {"domain": "light", "action": "set_warm_amber", "brightness": 65},
                    {"domain": "media", "action": "suggest_comfort_ambient", "genre": "acoustic_lofi"},
                    {"domain": "notification", "action": "suppress_non_urgent", "duration_minutes": 60}
                ]
            )
        if mood == MoodState.ANXIOUS_STRESSED:
            return (
                "INTERVENTION_DE_ESCALATION",
                "L'utente presenta tachicardia e marcata ansia/agitazione. Riduci immediatamente l'ambiguità: fornisci punti fermi e risposte strutturate ad elenco puntato. Mantieni un tono calmo e autorevole.",
                {"pitch_shift": -1.0, "speed": 0.92, "warmth_level": "high", "volume_db": -1.0},
                [
                    {"domain": "light", "action": "set_soft_neutral", "brightness": 50},
                    {"domain": "climate", "action": "refresh_ventilation", "target_temp": 20.5}
                ]
            )
        if mood == MoodState.FATIGUED_BURNOUT:
            return (
                "INTERVENTION_FATIGUE_PREVENTION",
                "L'utente mostra forte affaticamento e sonnolenza. Sii ultra-sintetico. Proponi di automatizzare i compiti in background o rimandare il lavoro al giorno successivo.",
                {"pitch_shift": 0.0, "speed": 0.95, "warmth_level": "medium", "volume_db": 0.0},
                [
                    {"domain": "display", "action": "enable_night_shift", "blue_filter": True}
                ]
            )
        return (
            "INTERVENTION_STANDARD_HIGH_PRODUCTIVITY",
            "L'utente è in stato emotivo bilanciato ed energico. Massima proattività operativa ed efficienza esecutiva.",
            {"pitch_shift": 0.0, "speed": 1.0, "warmth_level": "standard", "volume_db": 0.0},
            []
        )

    def compute_limbic_update(self, payload: PhysiologicalMultimodalPayload) -> Any:
        from server.core.kernel.domain.limbic_state import LimbicState
        res = self.infer_affective_state(payload)
        na = min(1.0, 0.15 + 0.6 * res.anxiety_stress_score)
        c = min(1.0, 0.10 + 0.5 * res.anxiety_stress_score + 0.3 * res.fatigue_burnout_score)
        d = max(0.1, 0.7 - 0.5 * res.depression_risk_score - 0.3 * res.fatigue_burnout_score)
        s = max(0.2, 0.8 - 0.5 * res.anxiety_stress_score)
        return LimbicState(dopamine=d, noradrenaline=na, serotonin=s, cortisol=c, last_update_ts=payload.timestamp)

affective_fusion_engine = AffectiveFusionEngine()
