import re
from typing import List, Tuple
from .interfaces import UserCognitiveInput, MethodologicalEvaluation

class MethodologicalAgent:
    def evaluate(self, user_input: UserCognitiveInput) -> MethodologicalEvaluation:
        text = user_input.raw_text.strip()
        complexity = self._calculate_complexity(text)
        overload = self._calculate_overload(text, user_input.gaze_stability, user_input.hrv_ms)
        socratic_steps, action_plan, scaffolding = self._generate_methodology(text, complexity, overload)

        return MethodologicalEvaluation(
            task_complexity=round(complexity, 2),
            overload_index=round(overload, 2),
            socratic_steps=socratic_steps,
            pragmatic_action_plan=action_plan,
            cognitive_scaffolding=scaffolding
        )

    def _calculate_complexity(self, text: str) -> float:
        words = len(text.split())
        clauses = len(re.split(r"[,;:.?!]", text))
        conjunctions = len(re.findall(r"\b(e|ma|perché|oppure|mentre|inoltre|sebbene|tuttavia)\b", text, re.IGNORECASE))
        raw_score = (words / 50.0) * 0.4 + (clauses / 6.0) * 0.3 + (conjunctions / 4.0) * 0.3
        return min(1.0, max(0.1, raw_score))

    def _calculate_overload(self, text: str, gaze_stability: float, hrv_ms: float) -> float:
        overload_words = len(re.findall(r"\b(non capisco|troppo|caos|confusione|mille cose|bloccato|non so da dove)\b", text, re.IGNORECASE))
        gaze_factor = max(0.0, 1.0 - gaze_stability)
        hrv_factor = 1.0 if hrv_ms < 30.0 else (0.5 if hrv_ms < 45.0 else 0.1)
        score = (overload_words * 0.35) + (gaze_factor * 0.35) + (hrv_factor * 0.3)
        return min(1.0, max(0.05, score))

    def _generate_methodology(self, text: str, complexity: float, overload: float) -> Tuple[List[str], List[str], str]:
        if overload > 0.6 or complexity > 0.7:
            socratic = [
                "Qual è il singolo fatto oggettivo che richiede attenzione immediata nei prossimi cinque minuti?",
                "Cosa può essere accantonato temporaneamente senza conseguenze irreversibili?",
                "Quale presupposto implicito sta generando la pressione percepita?"
            ]
            actions = [
                "Fermare l'elaborazione simultanea di più task.",
                "Selezionare una sola variabile controllabile.",
                "Eseguire unicamente il primo micro-passo circoscritto."
            ]
            scaffolding = "single_variable_isolation"
        else:
            socratic = [
                "Qual è l'obiettivo prioritario della sessione attuale?",
                "Quale criterio verificherà il compimento dell'azione?"
            ]
            actions = [
                "Procedere con l'esecuzione dell'azione diretta richiesta.",
                "Verificare la conformità del risultato."
            ]
            scaffolding = "linear_progressive_execution"

        return socratic, actions, scaffolding
