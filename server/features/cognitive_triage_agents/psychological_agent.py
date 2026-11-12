import re
from typing import Any, Tuple
from .interfaces import UserCognitiveInput, PsychologicalEvaluation, EmotionalState

class PsychologicalAgent:
    def __init__(self) -> None:
        self._distortion_patterns = {
            "catastrophizing": re.compile(r"\b(tutto è perduto|disastro|fine|mai più|terribile|non posso resistere|irreparabile|rovina)\b", re.IGNORECASE),
            "overgeneralization": re.compile(r"\b(sempre|mai|tutti|nessuno|ogni volta|inutile provarci)\b", re.IGNORECASE),
            "all_or_nothing": re.compile(r"\b(fallimento totale|perfetto o niente|incapace|non valgo nulla)\b", re.IGNORECASE),
            "hopelessness": re.compile(r"\b(non ce la faccio|arrendo|non serve a nulla|sfinito|stanco di tutto)\b", re.IGNORECASE)
        }

    def evaluate(self, user_input: UserCognitiveInput) -> PsychologicalEvaluation:
        text = user_input.raw_text.strip().lower()
        vocal_stress = 1.0 if user_input.vocal_jitter > 0.04 else (0.5 if user_input.vocal_jitter > 0.02 else 0.0)
        physio_stress = 1.0 if user_input.heart_rate_bpm > 105.0 or user_input.hrv_ms < 25.0 else 0.0
        
        detected_distortion = self._detect_distortion(text)
        emotional_state, empathy_depth = self._classify_state(text, user_input.facial_valence, vocal_stress, physio_stress)
        strategy, reframing = self._build_reframing(emotional_state, detected_distortion)

        return PsychologicalEvaluation(
            emotional_state=emotional_state,
            empathy_depth=round(empathy_depth, 2),
            cognitive_distortion=detected_distortion,
            deescalation_strategy=strategy,
            supportive_reframing=reframing
        )

    def _detect_distortion(self, text: str) -> str:
        for name, pattern in self._distortion_patterns.items():
            if pattern.search(text):
                return name
        return "none_detected"

    def _classify_state(self, text: str, valence: float, vocal_stress: float, physio_stress: float) -> Tuple[EmotionalState, float]:
        frustration_hits = len(re.findall(r"\b(arrabbiato|odio|basta|furioso|stufo|ingiusto)\b", text, re.IGNORECASE))
        anxiety_hits = len(re.findall(r"\b(ansia|panico|paura|angoscia|terrore|preoccupat)\b", text, re.IGNORECASE))
        depression_hits = len(re.findall(r"\b(triste|vuoto|piangere|depress|buio|inutile|solitudi)\b", text, re.IGNORECASE))
        overload_hits = len(re.findall(r"\b(troppo|non riesco a seguire|impazzisco|soffoco|pressione)\b", text, re.IGNORECASE))

        score = (vocal_stress * 0.3) + (physio_stress * 0.3) + (max(0.0, -valence) * 0.4)

        if depression_hits > 0:
            return EmotionalState.DEPRESSED, min(1.0, 0.7 + score * 0.3)
        if anxiety_hits > 0 or (physio_stress > 0.5 and vocal_stress > 0.5):
            return EmotionalState.ANXIOUS, min(1.0, 0.6 + score * 0.4)
        if valence < -0.4:
            return EmotionalState.DEPRESSED, min(1.0, 0.7 + score * 0.3)
        if frustration_hits > 0:
            return EmotionalState.FRUSTRATED, min(1.0, 0.5 + score * 0.5)
        if overload_hits > 0:
            return EmotionalState.OVERWHELMED, min(1.0, 0.6 + score * 0.4)
        
        return EmotionalState.CALM, max(0.1, score * 0.3)

    def _build_reframing(self, state: EmotionalState, distortion: str) -> Tuple[str, str]:
        if state == EmotionalState.DEPRESSED:
            return "active_compassionate_validation", "Riconoscere la fatica interiore senza forzare l'ottimismo, validando la vulnerabilità."
        if state == EmotionalState.ANXIOUS:
            return "grounding_and_somatic_anchoring", "Riportare l'attenzione sul momento presente riducendo la percezione di minaccia futura."
        if state == EmotionalState.OVERWHELMED:
            return "cognitive_load_reduction", "Sospendere le decisioni complesse e circoscrivere il campo d'azione."
        if state == EmotionalState.FRUSTRATED:
            return "non_defensive_deescalation", "Ascolto chiaro privo di reattività, offrendo uno spazio ordinato di sfogo."
        return "neutral_supportive", "Presenza equilibrata e attenta alla stabilità dell'utente."

    def detect_tom_discrepancy(self, user_input: UserCognitiveInput) -> Any:
        from server.core.kernel.domain.node import SynapticSpike
        text = user_input.raw_text.strip().lower()
        is_literal_positive = bool(re.search(r"\b(sto bene|tutto bene|tutto ok|nessun problema|va bene)\b", text))
        has_somatic_distress = (user_input.vocal_jitter > 0.03 or user_input.heart_rate_bpm > 95.0 or user_input.facial_valence < -0.25)
        if is_literal_positive and has_somatic_distress:
            return SynapticSpike(
                source_neuron="psychological_agent",
                target_cluster="theory_of_mind",
                potential=0.95,
                inhibitory_gaba=False,
                emotion_vector=[0.1, 0.8, 0.4, 0.7],
                payload={"override": True, "reason": "tom_discrepancy_detected", "text": text},
            )
        return None
