import math
import time
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

class ContextDimension(BaseModel):
    user_role: str = "user_primary"
    active_environment: str = "smart_home"
    available_plugins: List[str] = Field(default_factory=list)
    active_widgets: List[str] = Field(default_factory=list)
    system_load: float = 0.15
    privacy_mode: bool = False
    preferred_language: str = "it"

class CandidateAction(BaseModel):
    action_id: str
    target_agent: str
    subagent_id: Optional[str] = None
    required_tool: Optional[str] = None
    associated_widget: Optional[str] = None
    base_utility: float = 1.0
    execution_cost: float = 0.1
    privacy_risk: float = 0.0

class JevDecision(BaseModel):
    selected_action: CandidateAction
    expected_value: float
    confidence: float
    reasoning_vector: Dict[str, float]
    ranked_candidates: List[Dict[str, Any]]
    evaluation_time_ms: float

class JevDecisionEngine:
    def __init__(self) -> None:
        self._action_registry: Dict[str, CandidateAction] = {}
        self._register_default_candidates()

    def register_candidate(self, candidate: CandidateAction) -> None:
        self._action_registry[candidate.action_id] = candidate

    def evaluate(self, query: str, context: ContextDimension) -> JevDecision:
        t0 = time.perf_counter()
        query_lower = query.lower()
        scored_candidates: List[tuple[CandidateAction, float, Dict[str, float]]] = []

        for action_id, candidate in self._action_registry.items():
            prob_success = self._compute_success_probability(query_lower, candidate, context)
            utility = self._compute_utility(candidate, context)
            cost = candidate.execution_cost
            if context.system_load > 0.8:
                cost *= 1.5

            jev_score = (prob_success * utility) - cost

            if context.privacy_mode and candidate.privacy_risk > 0.3:
                jev_score -= 10.0

            vector = {
                "prob_success": round(prob_success, 4),
                "utility": round(utility, 4),
                "cost": round(cost, 4),
                "jev_score": round(jev_score, 4),
            }
            scored_candidates.append((candidate, jev_score, vector))

        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        best_candidate, best_score, best_vector = scored_candidates[0]

        ranked = [
            {
                "action_id": c.action_id,
                "agent": c.target_agent,
                "subagent": c.subagent_id,
                "tool": c.required_tool,
                "widget": c.associated_widget,
                "score": round(s, 4),
                "metrics": v,
            }
            for c, s, v in scored_candidates[:5]
        ]

        t1 = time.perf_counter()
        latency = (t1 - t0) * 1000.0

        confidence = 1.0 / (1.0 + math.exp(-best_score)) if best_score > 0 else 0.5

        return JevDecision(
            selected_action=best_candidate,
            expected_value=round(best_score, 4),
            confidence=round(confidence, 4),
            reasoning_vector=best_vector,
            ranked_candidates=ranked,
            evaluation_time_ms=round(latency, 2),
        )

    def _compute_success_probability(self, query: str, candidate: CandidateAction, ctx: ContextDimension) -> float:
        score = 0.1
        tokens = query.split()

        target_keywords = {
            "google_gmail": ["mail", "email", "gmail", "invia mail", "messaggio", "posta", "scrivi a"],
            "google_calendar": ["calendario", "calendar", "evento", "appuntamento", "riunione", "orario", "fissa"],
            "google_contacts": ["contatto", "contatti", "rubrica", "numero", "indirizzo", "persona", "trova contatto"],
            "google_classroom": ["classroom", "lezione", "compito", "corso", "materia", "studenti", "scuola"],
            "google_drive": ["drive", "file", "cartella", "documento", "pdf", "salva file", "upload"],
            "home_assistant": ["luci", "luce", "accendi", "spegni", "porta", "temperatura", "termostato"],
            "cad_engineer": ["cad", "dxf", "disegno", "dwg", "flangia", "ingegneria", "quota"],
            "social_media": ["instagram", "post", "copy", "social", "caption", "feed", "telegram"],
        }

        sub = candidate.subagent_id or candidate.target_agent
        keywords = target_keywords.get(sub, [])
        match_count = sum(1 for kw in keywords if kw in query)

        if match_count > 0:
            score += min(0.85, match_count * 0.4)

        if candidate.required_tool and candidate.required_tool in ctx.available_plugins:
            score += 0.1

        return min(0.99, max(0.01, score))

    def _compute_utility(self, candidate: CandidateAction, ctx: ContextDimension) -> float:
        utility = candidate.base_utility
        if ctx.user_role == "user_primary":
            utility *= 1.2
        if candidate.associated_widget and candidate.associated_widget in ctx.active_widgets:
            utility += 0.5
        return utility

    def _register_default_candidates(self) -> None:
        defaults = [
            CandidateAction(
                action_id="gmail_send_message",
                target_agent="google_suite_agent",
                subagent_id="google_gmail",
                required_tool="google_gmail_tool",
                associated_widget="gmail_composer_card",
                base_utility=2.8,
                execution_cost=0.15,
                privacy_risk=0.1,
            ),
            CandidateAction(
                action_id="calendar_schedule_event",
                target_agent="google_suite_agent",
                subagent_id="google_calendar",
                required_tool="google_calendar_tool",
                associated_widget="calendar_card",
                base_utility=2.6,
                execution_cost=0.12,
                privacy_risk=0.05,
            ),
            CandidateAction(
                action_id="contacts_lookup_person",
                target_agent="google_suite_agent",
                subagent_id="google_contacts",
                required_tool="google_contacts_tool",
                associated_widget="contacts_card",
                base_utility=2.4,
                execution_cost=0.1,
                privacy_risk=0.2,
            ),
            CandidateAction(
                action_id="classroom_manage_course",
                target_agent="google_suite_agent",
                subagent_id="google_classroom",
                required_tool="google_classroom_tool",
                associated_widget="classroom_card",
                base_utility=2.5,
                execution_cost=0.14,
                privacy_risk=0.1,
            ),
            CandidateAction(
                action_id="drive_sync_file",
                target_agent="google_suite_agent",
                subagent_id="google_drive",
                required_tool="google_drive_tool",
                associated_widget="drive_card",
                base_utility=2.7,
                execution_cost=0.18,
                privacy_risk=0.15,
            ),
            CandidateAction(
                action_id="smart_home_toggle",
                target_agent="agent_home_assistant",
                subagent_id="home_assistant",
                required_tool="homeassistant_toggle",
                associated_widget="smart_switch",
                base_utility=3.0,
                execution_cost=0.08,
                privacy_risk=0.0,
            ),
            CandidateAction(
                action_id="cad_generate_dxf",
                target_agent="autocad_designer",
                subagent_id="cad_engineer",
                required_tool="cad_generate_dxf",
                associated_widget="cad_viewer",
                base_utility=2.9,
                execution_cost=0.25,
                privacy_risk=0.0,
            ),
            CandidateAction(
                action_id="social_instagram_draft",
                target_agent="instagram_agent",
                subagent_id="social_media",
                required_tool="instagram_generate_copy",
                associated_widget="social_post_preview",
                base_utility=2.5,
                execution_cost=0.12,
                privacy_risk=0.05,
            ),
        ]
        for d in defaults:
            self.register_candidate(d)

jev_engine = JevDecisionEngine()
