import re
import time
from dataclasses import dataclass, field
from typing import Any

from features.team.board import board
from features.team.scanner import DiscoveredAgent, scanner
from state import store

WORD_RE = re.compile(r"[a-zà-ÿ0-9_-]{3,}", re.IGNORECASE)


@dataclass
class CEODecision:
    primary_agent: DiscoveredAgent
    secondary_agents: list[DiscoveredAgent]
    delegation_plan: str
    confidence: float
    timestamp: float = field(default_factory=time.time)


class CEOExecutive:
    """
    CEO Orchestrator dinamico di Nuxiva:
    Non possiede un elenco fisso o cablato di agenti. All'avvio e a ogni richiesta,
    utilizza uno scanner che analizza dinamicamente le cartelle di sistema e utente,
    identificando gli agenti presenti, i loro strumenti (tools), widget e capacità.
    Su questa base in tempo reale, il CEO formula il piano di coordinamento e delega.
    """

    def __init__(self) -> None:
        self.scanner = scanner

    def scan_team(self, force: bool = False) -> dict[str, DiscoveredAgent]:
        return self.scanner.scan(force=force)

    def analyze_request(self, text: str, context: dict | None = None) -> CEODecision:
        agents = self.scan_team()
        query = (text or "").strip().lower()
        query_words = set(w.lower() for w in WORD_RE.findall(query))

        scores: dict[str, float] = {}

        for aid, agent in agents.items():
            score = 0.0

            # 1. Corrispondenza con nome o id dell'agente
            if agent.name.lower() in query or aid in query:
                score += 4.0

            # 2. Corrispondenza con le capacità dichiarate
            for cap in agent.capabilities:
                cap_words = set(w.lower() for w in WORD_RE.findall(cap))
                common = query_words.intersection(cap_words)
                if common:
                    score += 2.0 * len(common)

            # 3. Corrispondenza con gli strumenti dell'agente (tools)
            for t in agent.tools:
                tname = t["name"].lower()
                if tname in query or any(kw in query for kw in tname.split("_")):
                    score += 2.5
                tdesc_words = set(w.lower() for w in WORD_RE.findall(t.get("description", "")))
                common_tools = query_words.intersection(tdesc_words)
                if common_tools:
                    score += 1.5 * len(common_tools)

            # 4. Corrispondenza con i widget dell'agente
            for w in agent.widgets:
                wname = w["name"].lower()
                if wname in query:
                    score += 2.0
                for intent in w.get("intents", []):
                    if intent.lower() in query:
                        score += 2.0

            # 5. Corrispondenza con la descrizione dell'agente
            desc_words = set(w.lower() for w in WORD_RE.findall(agent.description))
            common_desc = query_words.intersection(desc_words)
            if common_desc:
                score += 1.0 * len(common_desc)

            # 6. Corrispondenza semantica generale con i token indicizzati
            common_kw = query_words.intersection(agent.keywords)
            score += 0.4 * len(common_kw)

            scores[aid] = score

        # Ordinamento degli agenti per punteggio
        sorted_agents = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        primary: DiscoveredAgent
        secondaries: list[DiscoveredAgent] = []

        if sorted_agents and sorted_agents[0][1] > 0.0:
            top_id, top_score = sorted_agents[0]
            primary = agents[top_id]
            for aid, sc in sorted_agents[1:4]:
                if sc > 0:
                    secondaries.append(agents[aid])
            confidence = min(1.0, 0.4 + (top_score * 0.1))
        else:
            # Fallback dinamico: cerca l'agente più orientato al dialogo/ragionamento
            fallback_candidates = ["chat", "brain", "understanding", "agent"]
            primary_id = next((f for f in fallback_candidates if f in agents), list(agents.keys())[0] if agents else "agent")
            primary = agents.get(primary_id) or DiscoveredAgent(
                id="agent", name="Assistente Generale", description="Coordinamento cognitivo e conversazione"
            )
            confidence = 0.5

        tool_count = len(primary.tools)
        widget_count = len(primary.widgets)
        plan = (
            f"Il CEO ha scansionato la squadra ({len(agents)} agenti, "
            f"{sum(len(a.tools) for a in agents.values())} strumenti, "
            f"{sum(len(a.widgets) for a in agents.values())} widget) "
            f"e assegna l'incarico a «{primary.name}» [{primary.id}] "
            f"({tool_count} strumenti, {widget_count} widget)."
        )
        if secondaries:
            plan += f" Supporto assegnato a: {', '.join(s.name for s in secondaries)}."

        return CEODecision(
            primary_agent=primary,
            secondary_agents=secondaries,
            delegation_plan=plan,
            confidence=confidence
        )

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
        agent_name = decision.primary_agent.name

        result["ceo"] = {
            "orchestrator": "CEO Executive",
            "delegated_to": decision.primary_agent.id,
            "specialist": agent_name,
            "category": decision.primary_agent.category,
            "tools_count": len(decision.primary_agent.tools),
            "widgets_count": len(decision.primary_agent.widgets),
            "plan": decision.delegation_plan,
            "confidence": decision.confidence
        }

        current_agent = result.get("agent")
        if not current_agent or current_agent in ("core", "nuxiva_ui", "assistente"):
            result["agent"] = f"CEO → {agent_name}"
        elif not current_agent.startswith("CEO"):
            result["agent"] = f"CEO [{agent_name}] · {current_agent}"

        board.post("ceo", "tutti", f"Incarico completato con successo da {agent_name}", "conferma")
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
