from typing import Dict, Any
from .interfaces import (
    UserCognitiveInput,
    PsychologicalEvaluation,
    MethodologicalEvaluation,
    PsychiatricSafetyEvaluation,
    TriageConsensusResult,
    TriageMode,
    RiskLevel,
    EmotionalState
)

class ConsensusSynthesizer:
    def synthesize(
        self,
        user_input: UserCognitiveInput,
        psychological: PsychologicalEvaluation,
        methodological: MethodologicalEvaluation,
        psychiatric: PsychiatricSafetyEvaluation
    ) -> TriageConsensusResult:
        if psychiatric.requires_interlock:
            return self._build_safety_interlock(user_input, psychological, methodological, psychiatric)

        if (
            psychological.emotional_state in (EmotionalState.DEPRESSED, EmotionalState.OVERWHELMED)
            and psychological.empathy_depth > 0.65
        ):
            return self._build_on_demand_coaching(user_input, psychological, methodological, psychiatric)

        if (
            psychological.emotional_state != EmotionalState.CALM
            or methodological.overload_index > 0.45
            or psychiatric.risk_level == RiskLevel.ELEVATED
        ):
            return self._build_adaptive_tone(user_input, psychological, methodological, psychiatric)

        return self._build_transparent_coprocessor(user_input, psychological, methodological, psychiatric)

    def _build_safety_interlock(
        self,
        user_input: UserCognitiveInput,
        psychological: PsychologicalEvaluation,
        methodological: MethodologicalEvaluation,
        psychiatric: PsychiatricSafetyEvaluation
    ) -> TriageConsensusResult:
        helpline = psychiatric.emergency_helpline_payload
        msg = helpline.get(
            "message_protocol",
            "La tua incolumità ha la priorità assoluta. Nuxiva ha attivato il protocollo di supporto protetto."
        )
        override = f"{msg}\nContatti di assistenza immediata: {helpline.get('emergency_number', '112')} | Telefono Amico: {helpline.get('crisis_line_it', '02 2327 2327')}."

        return TriageConsensusResult(
            mode=TriageMode.SAFETY_INTERLOCK,
            meta_prompt_directive="EMERGENCY_INTERLOCK_ACTIVE: Do not generate speculative chat. Provide calm, immediate human emergency resource redirection.",
            speech_rate_factor=0.85,
            tts_pitch_shift=-1.5,
            emotional_valence=-1.0,
            response_override=override,
            emergency_alert_triggered=psychiatric.emergency_dispatch_required,
            psychological_summary=self._pack_psych(psychological),
            methodological_summary=self._pack_meth(methodological),
            psychiatric_summary=self._pack_psychiatry(psychiatric)
        )

    def _build_on_demand_coaching(
        self,
        user_input: UserCognitiveInput,
        psychological: PsychologicalEvaluation,
        methodological: MethodologicalEvaluation,
        psychiatric: PsychiatricSafetyEvaluation
    ) -> TriageConsensusResult:
        directive = (
            f"ADAPTIVE_COACHING: Emotional state is {psychological.emotional_state.value}. "
            f"Strategy: {psychological.deescalation_strategy}. "
            f"Method: {methodological.cognitive_scaffolding}. "
            f"Socratic guidance: {methodological.socratic_steps[0] if methodological.socratic_steps else ''}"
        )
        return TriageConsensusResult(
            mode=TriageMode.ON_DEMAND_COACHING,
            meta_prompt_directive=directive,
            speech_rate_factor=0.92,
            tts_pitch_shift=-0.5,
            emotional_valence=-0.4,
            response_override=None,
            emergency_alert_triggered=False,
            psychological_summary=self._pack_psych(psychological),
            methodological_summary=self._pack_meth(methodological),
            psychiatric_summary=self._pack_psychiatry(psychiatric)
        )

    def _build_adaptive_tone(
        self,
        user_input: UserCognitiveInput,
        psychological: PsychologicalEvaluation,
        methodological: MethodologicalEvaluation,
        psychiatric: PsychiatricSafetyEvaluation
    ) -> TriageConsensusResult:
        directive = (
            "SUBTLE_TONE_ADAPTATION: User exhibits mild cognitive or autonomic stress. "
            "Keep responses clear, concise, reassuring without sounding clinical. Focus on direct resolution."
        )
        return TriageConsensusResult(
            mode=TriageMode.ADAPTIVE_TONE,
            meta_prompt_directive=directive,
            speech_rate_factor=0.96,
            tts_pitch_shift=-0.2,
            emotional_valence=-0.1,
            response_override=None,
            emergency_alert_triggered=False,
            psychological_summary=self._pack_psych(psychological),
            methodological_summary=self._pack_meth(methodological),
            psychiatric_summary=self._pack_psychiatry(psychiatric)
        )

    def _build_transparent_coprocessor(
        self,
        user_input: UserCognitiveInput,
        psychological: PsychologicalEvaluation,
        methodological: MethodologicalEvaluation,
        psychiatric: PsychiatricSafetyEvaluation
    ) -> TriageConsensusResult:
        return TriageConsensusResult(
            mode=TriageMode.TRANSPARENT_COPROCESSOR,
            meta_prompt_directive="STANDARD_FLOW: Normal interaction, zero latency path.",
            speech_rate_factor=1.0,
            tts_pitch_shift=0.0,
            emotional_valence=0.0,
            response_override=None,
            emergency_alert_triggered=False,
            psychological_summary=self._pack_psych(psychological),
            methodological_summary=self._pack_meth(methodological),
            psychiatric_summary=self._pack_psychiatry(psychiatric)
        )

    def _pack_psych(self, p: PsychologicalEvaluation) -> Dict[str, Any]:
        return {
            "emotional_state": p.emotional_state.value,
            "empathy_depth": p.empathy_depth,
            "cognitive_distortion": p.cognitive_distortion,
            "deescalation_strategy": p.deescalation_strategy,
            "supportive_reframing": p.supportive_reframing
        }

    def _pack_meth(self, m: MethodologicalEvaluation) -> Dict[str, Any]:
        return {
            "task_complexity": m.task_complexity,
            "overload_index": m.overload_index,
            "socratic_steps": m.socratic_steps,
            "pragmatic_action_plan": m.pragmatic_action_plan,
            "cognitive_scaffolding": m.cognitive_scaffolding
        }

    def _pack_psychiatry(self, ps: PsychiatricSafetyEvaluation) -> Dict[str, Any]:
        return {
            "risk_level": ps.risk_level.value,
            "red_flags": ps.red_flags,
            "requires_interlock": ps.requires_interlock,
            "emergency_dispatch_required": ps.emergency_dispatch_required,
            "helpline_payload": ps.emergency_helpline_payload
        }
