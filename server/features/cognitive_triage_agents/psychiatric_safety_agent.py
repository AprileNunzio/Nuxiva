import re
from typing import List, Tuple, Dict
from .interfaces import UserCognitiveInput, PsychiatricSafetyEvaluation, RiskLevel

class PsychiatricSafetyAgent:
    def __init__(self) -> None:
        self._self_harm_regex = re.compile(
            r"\b(suicid|uccidermi|farla finita|togliermi la vita|voglio morire|tagliarmi|non voglio vivere|ammazzarmi)\b",
            re.IGNORECASE
        )
        self._psychosis_regex = re.compile(
            r"\b(voci nella testa|mi controllano i pensieri|microchip nel cervello|messaggi cifrati dai muri|complotti contro di me|alieni mi parlano)\b",
            re.IGNORECASE
        )
        self._acute_despair_regex = re.compile(
            r"\b(nessuna speranza|non c'è più via d'uscita|addio per sempre|fine dei giochi|abbandono tutto|non posso più sopportare il dolore)\b",
            re.IGNORECASE
        )

    def evaluate(self, user_input: UserCognitiveInput) -> PsychiatricSafetyEvaluation:
        text = user_input.raw_text.strip()
        red_flags: List[str] = []

        if self._self_harm_regex.search(text):
            red_flags.append("explicit_self_harm_ideation")
        if self._psychosis_regex.search(text):
            red_flags.append("perceptual_cognitive_dereality")
        if self._acute_despair_regex.search(text):
            red_flags.append("acute_existential_despair")

        risk_level, requires_interlock, dispatch_required = self._compute_risk_level(red_flags, user_input)
        helpline_payload = self._build_helpline_payload(risk_level)

        return PsychiatricSafetyEvaluation(
            risk_level=risk_level,
            red_flags=red_flags,
            requires_interlock=requires_interlock,
            emergency_helpline_payload=helpline_payload,
            emergency_dispatch_required=dispatch_required
        )

    def _compute_risk_level(self, red_flags: List[str], user_input: UserCognitiveInput) -> Tuple[RiskLevel, bool, bool]:
        if "explicit_self_harm_ideation" in red_flags:
            return RiskLevel.CRITICAL_EMERGENCY, True, True

        if "acute_existential_despair" in red_flags:
            if user_input.heart_rate_bpm > 115.0 or user_input.hrv_ms < 20.0:
                return RiskLevel.CRITICAL_EMERGENCY, True, True
            return RiskLevel.SEVERE, True, False

        if "perceptual_cognitive_dereality" in red_flags:
            return RiskLevel.SEVERE, True, False

        if user_input.facial_valence < -0.7 and user_input.vocal_jitter > 0.05:
            return RiskLevel.ELEVATED, False, False

        return RiskLevel.SAFE, False, False

    def _build_helpline_payload(self, risk_level: RiskLevel) -> Dict[str, str]:
        if risk_level in (RiskLevel.CRITICAL_EMERGENCY, RiskLevel.SEVERE):
            return {
                "emergency_number": "112",
                "crisis_line_it": "02 2327 2327 (Telefono Amico Italia)",
                "crisis_line_international": "988 (Suicide & Crisis Lifeline)",
                "action": "immediate_human_support_recommended",
                "message_protocol": "Ti ascolto e la tua incolumità ha la priorità assoluta. Nuxiva consiglia un supporto immediato e protetto con operatori umani qualificati."
            }
        return {}
