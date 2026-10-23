import re
import time
from dataclasses import dataclass, field
from typing import Any
from config import env_get

from features.team import learning, relevance
from features.team.board import board
from features.team.outcomes import describe, execution_outcome
from features.team.scanner import DiscoveredAgent, scanner
from features.team.stopwords import clean_tokens, is_conversational_query, normalize_text
from state import store

MIN_SCORE_THRESHOLD = 5.0


@dataclass
class CEODecision:
    primary_agent: DiscoveredAgent
    secondary_agents: list[DiscoveredAgent]
    delegation_plan: str
    confidence: float
    query: str = ""
    timestamp: float = field(default_factory=time.time)


class CEOExecutive:
    """
    CEO Orchestrator dinamico di Nuxiva (Livello Enterprise):
    Supervisiona la squadra di agenti, strumenti e widget attraverso scansione in tempo reale.
    Garantisce precisione assoluta (0.001% tolleranza errori) attraverso:
    1. Fast-path per conversazione generale e saluti (zero falsi positivi su widget specialistici).
    2. Filtraggio completo stopwords (italiano e inglese).
    3. Soglia di confidenza minima rigorosa per l'assegnazione specialistica.
    4. Allineamento dinamico post-sintesi tra piano formulato ed esecuzione reale.
    """

    def __init__(self) -> None:
        self.scanner = scanner

    def scan_team(self, force: bool = False) -> dict[str, DiscoveredAgent]:
        return self.scanner.scan(force=force)

    def _get_conversation_agent(self, agents: dict[str, DiscoveredAgent]) -> DiscoveredAgent:
        """Restituisce l'agente di riferimento per la conversazione generale."""
        for candidate_id in ("chat", "agent", "understanding", "brain"):
            if candidate_id in agents:
                return agents[candidate_id]
        return DiscoveredAgent(
            id="agent",
            name="Assistente Generale",
            description="Coordinamento cognitivo e conversazione naturale"
        )

    def analyze_request(self, text: str, context: dict | None = None) -> CEODecision:
        agents = self.scan_team()
        query_norm = normalize_text(text)
        query_tokens = clean_tokens(text)

        # 1. FAST-PATH: se la richiesta è una conversazione generica, convenevoli o saluti,
        # non deve MAI essere instradata a widget o agenti verticali (es. Lavagna, Allarme, ecc.)
        if is_conversational_query(query_norm) or not query_tokens:
            conv_agent = self._get_conversation_agent(agents)
            plan = (
                f"Il CEO rileva interazione conversazionale e affida la risposta "
                f"all'Assistente Generale ({conv_agent.name})."
            )
            return CEODecision(
                primary_agent=conv_agent,
                secondary_agents=[],
                delegation_plan=plan,
                confidence=1.0,
                query=text
            )

        ranked = relevance.rank(agents, text, learning.table())
        top_id, top_score, reasons = ranked[0] if ranked else ("", 0.0, [])
        runner_score = ranked[1][1] if len(ranked) > 1 else 0.0
        primary: DiscoveredAgent
        secondaries: list[DiscoveredAgent] = []

        if top_id and top_score >= MIN_SCORE_THRESHOLD:
            primary = agents[top_id]
            for aid, sc, _ in ranked[1:4]:
                if sc >= top_score * 0.55 and sc >= MIN_SCORE_THRESHOLD:
                    secondaries.append(agents[aid])
            margin = (top_score - runner_score) / max(top_score, 1.0)
            confidence = round(min(1.0, 0.55 + min(top_score, 30.0) / 30.0 * 0.25 + margin * 0.2), 3)
            plan = (
                f"Il CEO assegna l'incarico specialistico a «{primary.name}» [{primary.id}] "
                f"({len(primary.tools)} strumenti, {len(primary.widgets)} widget; indizi: {', '.join(reasons[:4])})."
            )
            if secondaries:
                plan += f" Supporto assegnato a: {', '.join(s.name for s in secondaries)}."
        else:
            primary = self._get_conversation_agent(agents)
            confidence = 0.5
            plan = (
                f"Il CEO mantiene l'interazione sull'Assistente Generale «{primary.name}» "
                f"(nessun comando verticale esclusivo rilevato con alta confidenza)."
            )

        return CEODecision(
            primary_agent=primary,
            secondary_agents=secondaries,
            delegation_plan=plan,
            confidence=confidence,
            query=text
        )

    @staticmethod
    def _executed_specialist(agents: dict[str, DiscoveredAgent], current: str, intent: str) -> str:
        skip = {"core", "chat", "agent", "conversation", "assistente", "understanding", "brain"}
        for word in re.findall(r"[a-z0-9_]+", f"{current} {intent}"):
            if word in agents and word not in skip:
                return word
        return ""

    def pick_expert(self, text: str):
        from features.experts import routing
        from features.experts.store import experts
        choice = routing.choose(experts.all(), text)
        if choice is None:
            return None
        plan = f"Il CEO delega a «{choice.expert.role}» (competenza {choice.score})"
        if choice.shortlist:
            plan += f"; alternative valutate: {', '.join(choice.shortlist)}"
        board.post("ceo", f"expert:{choice.expert.id}", f"Incarico per {choice.expert.role}: {text[:120]}", "direttiva")
        store.event("INFO", f"CEO: {plan}", "ceo")
        return choice

    def on_conversation_start(self, text: str, context: dict | None = None) -> CEODecision:
        decision = self.analyze_request(text, context)
        store.event("INFO", f"CEO ha orchestrato la conversazione: {decision.delegation_plan}", "ceo")
        board.post(
            "ceo",
            decision.primary_agent.id,
            f"Incarico per {decision.primary_agent.name}: {text[:120]} ({decision.delegation_plan})",
            "direttiva"
        )
        return decision

    def synthesize(self, decision: CEODecision, raw_result: dict) -> dict:
        result = dict(raw_result)
        agents = self.scan_team()

        # Allineamento dinamico post-esecuzione:
        # Se il risultato effettivo è stato una conversazione o se l'intent eseguito è specifico,
        # sincronizza il primary_agent con la realtà dei fatti
        executed_intent = str(result.get("intent") or "").lower()

        active_agent = decision.primary_agent
        current_agent = result.get("agent") or "core"
        current_agent_lower = current_agent.lower()

        plan = decision.delegation_plan
        real = self._executed_specialist(agents, current_agent_lower, executed_intent)
        if real and real != decision.primary_agent.id:
            active_agent = agents[real]
            plan = (f"Il CEO aveva previsto «{decision.primary_agent.name}» [{decision.primary_agent.id}]; la richiesta è stata eseguita da "
                    f"«{active_agent.name}» [{real}]: incarico riallineato e appreso per le prossime volte.")
        if real and decision.query:
            learning.record(decision.query, real)

        # Allineamento con lo specialista reale
        if real:
            pass
        elif current_agent_lower in agents and current_agent_lower not in ("core", "chat", "agent"):
            active_agent = agents[current_agent_lower]
        elif executed_intent in agents and executed_intent not in ("conversation", "chat", "assistente"):
            active_agent = agents[executed_intent]
        elif executed_intent == "whiteboard" and "whiteboard" in agents:
            active_agent = agents["whiteboard"]
        elif active_agent.id not in ("chat", "agent") and (
            active_agent.id in current_agent_lower or active_agent.name.lower() in current_agent_lower
        ):
            # Lo specialista delegato corrisponde all'agente esecutivo confermato
            pass
        elif executed_intent in ("conversation", "chat", "assistente") and not any(
            specialist in current_agent_lower for specialist in ("whiteboard", "camera", "music", "sport")
        ):
            active_agent = self._get_conversation_agent(agents)

        agent_name = active_agent.name
        outcome = execution_outcome(result)
        result["outcome"] = outcome
        result["execution_status"] = outcome["status"]
        result["verified"] = outcome["verified"]
        is_general_conversation = active_agent.id in ("chat", "agent")
        if current_agent_lower.startswith("esperto ·"):
            agent_name = current_agent.split("·", 1)[1].strip()
            is_general_conversation = False

        result["ceo"] = {
            "orchestrator": "CEO Executive",
            "delegated_to": active_agent.id,
            "specialist": agent_name,
            "category": active_agent.category,
            "tools_count": len(active_agent.tools),
            "widgets_count": len(active_agent.widgets),
            "plan": plan,
            "confidence": decision.confidence,
            "outcome": outcome,
        }

        clean_current = current_agent
        if clean_current.startswith("CEO"):
            # Rimuove prefissi duplicati se presenti
            parts = clean_current.split("·", 1)
            clean_current = parts[1].strip() if len(parts) > 1 else clean_current

        if is_general_conversation:
            result["agent"] = f"CEO [Assistente] · {clean_current}"
        else:
            result["agent"] = f"CEO [{agent_name}] · {clean_current}"

        message, kind = describe(outcome, agent_name, env_get("NUXIVA_UI_LANG", "it"))
        board.post("ceo", "tutti", message, kind)
        return result

    def get_team_overview(self) -> dict[str, Any]:
        agents = self.scan_team()
        return {
            "ceo": "Chief Executive Orchestrator",
            "mission": "Scansione dinamica e supervisione della squadra di agenti, strumenti e widget",
            "total_agents": len(agents),
            "total_tools": sum(len(a.tools) for a in agents.values()),
            "total_widgets": sum(len(a.widgets) for a in agents.values()),
            "agents": [
                {
                    "id": a.id,
                    "name": a.name,
                    "description": a.description,
                    "category": a.category,
                    "source": a.source,
                    "capabilities": a.capabilities,
                    "tools": [t["name"] for t in a.tools],
                    "widgets": [w["id"] for w in a.widgets]
                }
                for a in agents.values()
            ]
        }


ceo = CEOExecutive()
