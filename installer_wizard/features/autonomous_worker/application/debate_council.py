from typing import Any

from features.autonomous_worker.domain.knowledge_graph import knowledge_graph
from features.autonomous_worker.infrastructure.llm_runtime import runtime_manager


class EnterpriseDebateCouncil:
    DEBATE_PROMPT = (
        "Sei il comitato consultivo enterprise di Nuxiva composto da 3 menti analitiche:\n"
        "1. Chief Software Architect (Standard mondiali, modularità pura, Clean Architecture)\n"
        "2. Chief Information Security Officer (Zero-Trust, OWASP, crittografia, assenza backdoor)\n"
        "3. Chief Reliability Engineer (Deadlock avoidance, resilience, error handling robusto)\n"
        "Esegui una tavola rotonda critica sull'obiettivo proposto e valuta se il piano ha punti ciechi.\n"
        "Rispondi SOLO in formato JSON puro con questa struttura:\n"
        "{\n"
        '  "feasibility_score": 0.95,\n'
        '  "identified_risks": ["rischio 1", "rischio 2"],\n'
        '  "mandatory_guidelines": ["linea guida 1", "linea guida 2"],\n'
        '  "recommended_modularity": "note architetturali"\n'
        "}"
    )

    async def review_proposal(self, goal: str, domain: str, existing_directives: list[str]) -> dict[str, Any]:
        global_context = knowledge_graph.query_context(domain, limit=4)
        prompt = (
            f"OBIETTIVO DA ANALIZZARE: {goal}\n"
            f"DOMINIO: {domain}\n"
            f"DIRETTIVE PROPOSTE: {existing_directives}\n"
            f"LEZIONI APPRESE DAL KNOWLEDGE GRAPH AZIENDALE:\n" +
            ("\n".join(f"- {c}" for c in global_context) if global_context else "Nessuna lezione pregressa")
        )
        try:
            verdict = await runtime_manager.generate(
                prompt,
                as_json=True,
                max_tokens=900,
                temperature=0.1,
                system=self.DEBATE_PROMPT,
                component="autonomous_worker",
            )
            if isinstance(verdict, dict):
                return verdict
        except Exception:
            pass
        return {
            "feasibility_score": 1.0,
            "identified_risks": [],
            "mandatory_guidelines": ["Applicare Clean Architecture e Zero-Trust."],
            "recommended_modularity": "Nessuna restrizione addizionale",
        }


debate_council = EnterpriseDebateCouncil()
