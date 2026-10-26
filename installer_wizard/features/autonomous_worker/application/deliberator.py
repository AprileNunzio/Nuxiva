import hashlib
import json
import re
import time
from typing import Any

from features.autonomous_worker.infrastructure.llm_runtime import runtime_manager
from features.team.scanner import scanner
from features.autonomous_worker.domain.models import (
    AcceptanceCriteria,
    Mission,
    MissionQuestion,
    MissionStatus,
    Phase,
    Task,
    TaskStatus,
)
from features.autonomous_worker.domain.sanitizer import sanitize_text

SYSTEM_PROMPT = (
    "Sei il Chief Executive Architect di Nuxiva: operi al vertice degli standard mondiali, "
    "analitico, severo e orientato all'eccellenza. Per qualsiasi dominio operativo (software, "
    "ricerca, finanza, sicurezza, legale, design 3D, devops, strategia), produci un piano "
    "rigoroso scomposto in fasi, task con criteri di accettazione oggettivi e identifica eventuali "
    "domande o opzioni chiave per l'utente qualora esistano trade-off fondamentali. "
    "Rispondi esclusivamente con un oggetto JSON valido privo di markdown."
)


def _generate_mission_id(goal: str) -> str:
    seed = f"{goal}:{time.time()}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8]
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", goal.lower()).strip("-")[:24]
    return f"msn-{slug}-{digest}" if slug else f"msn-{digest}"


class MissionDeliberator:
    def __init__(self) -> None:
        self.scanner = scanner

    async def deliberate(
        self,
        goal: str,
        lang: str = "it",
        directives: list[str] | None = None,
        options: dict[str, Any] | None = None,
        mission_id: str | None = None,
    ) -> Mission:
        directives = directives or []
        options = options or {}
        available_agents = self.scanner.scan()
        capabilities_summary = [
            f"- {a.name} [{a.id}]: {len(a.tools)} tools, {len(a.widgets)} widgets, caps: {', '.join(a.capabilities[:3])}"
            for a in list(available_agents.values())[:25]
        ]

        prompt = (
            f"OBIETTIVO MISSIONE: {goal}\n"
            f"LINGUA DI INTERAZIONE: {lang}\n"
            f"DIRETTIVE PROPRIETARIO:\n" + ("\n".join(f"- {d}" for d in directives) if directives else "Nessuna") + "\n"
            f"OPZIONI ATTUALI: {json.dumps(options, ensure_ascii=False)}\n"
            f"CAPACITA GIA DISPONIBILI NEL SISTEMA:\n" + "\n".join(capabilities_summary) + "\n\n"
            "ISTRUZIONI FORMATO RISPOSTA (JSON PURO):\n"
            "{\n"
            '  "title": "Titolo professionale sintetico",\n'
            '  "domain": "software|security|research|finance|legal|3d_cad|devops|creative|other",\n'
            '  "questions": [\n'
            '    {\n'
            '      "id": "q1",\n'
            '      "question": "Testo chiaro della domanda o dubbio",\n'
            '      "options": ["Opzione A (Consigliata)", "Opzione B", "Opzione C"],\n'
            '      "is_multi_select": false,\n'
            '      "rationale": "Perché questa scelta incide sulla missione"\n'
            '    }\n'
            '  ],\n'
            '  "phases": [\n'
            '    {\n'
            '      "id": "p1",\n'
            '      "title": "Nome Fase (es. Architettura e Benchmark)",\n'
            '      "description": "Scopo della fase",\n'
            '      "tasks": [\n'
            '        {\n'
            '          "id": "t1",\n'
            '          "title": "Azione specifica",\n'
            '          "description": "Dettaglio esecutivo",\n'
            '          "specialist_role": "Ruolo esperto ideale",\n'
            '          "depends_on": [],\n'
            '          "criteria": [\n'
            '            {"description": "Criterio di accettazione oggettivo", "target": "misura o deliverable"}\n'
            '          ]\n'
            '        }\n'
            '      ]\n'
            '    }\n'
            '  ]\n'
            "}"
        )

        reply = await runtime_manager.generate(
            prompt,
            as_json=True,
            max_tokens=3200,
            temperature=0.2,
            system=SYSTEM_PROMPT,
            component="autonomous_worker",
        )
        if not isinstance(reply, dict):
            reply = {}

        mid = mission_id or _generate_mission_id(goal)
        title = sanitize_text(reply.get("title") or goal[:40], 120)
        domain = sanitize_text(reply.get("domain") or "general", 40)

        questions: list[MissionQuestion] = []
        for raw_q in reply.get("questions", []) if isinstance(reply.get("questions"), list) else []:
            if isinstance(raw_q, dict) and raw_q.get("question"):
                questions.append(
                    MissionQuestion(
                        id=str(raw_q.get("id") or f"q{len(questions) + 1}"),
                        question=sanitize_text(raw_q.get("question"), 300),
                        options=[sanitize_text(opt, 120) for opt in raw_q.get("options", []) if isinstance(opt, str)],
                        is_multi_select=bool(raw_q.get("is_multi_select", False)),
                        rationale=sanitize_text(raw_q.get("rationale", ""), 200),
                    )
                )

        phases: list[Phase] = []
        for raw_p in reply.get("phases", []) if isinstance(reply.get("phases"), list) else []:
            if not isinstance(raw_p, dict):
                continue
            pid = str(raw_p.get("id") or f"p{len(phases) + 1}")
            tasks: list[Task] = []
            for raw_t in raw_p.get("tasks", []) if isinstance(raw_p.get("tasks"), list) else []:
                if not isinstance(raw_t, dict):
                    continue
                tid = str(raw_t.get("id") or f"t{len(tasks) + 1}")
                criteria: list[AcceptanceCriteria] = []
                for raw_c in raw_t.get("criteria", []) if isinstance(raw_t.get("criteria"), list) else []:
                    if isinstance(raw_c, dict) and raw_c.get("description"):
                        criteria.append(
                            AcceptanceCriteria(
                                description=sanitize_text(raw_c.get("description"), 200),
                                target=sanitize_text(raw_c.get("target", ""), 100),
                            )
                        )
                tasks.append(
                    Task(
                        id=tid,
                        phase_id=pid,
                        title=sanitize_text(raw_t.get("title") or tid, 150),
                        description=sanitize_text(raw_t.get("description") or "", 500),
                        specialist_role=sanitize_text(raw_t.get("specialist_role") or "Specialista", 80),
                        depends_on=[str(d) for d in raw_t.get("depends_on", [])],
                        status=TaskStatus.PENDING,
                        criteria=criteria,
                    )
                )
            phases.append(
                Phase(
                    id=pid,
                    title=sanitize_text(raw_p.get("title") or pid, 100),
                    description=sanitize_text(raw_p.get("description") or "", 300),
                    tasks=tasks,
                )
            )

        has_blocking_questions = any(not q.answered and q.options for q in questions)
        initial_status = MissionStatus.QUESTION if has_blocking_questions else MissionStatus.RUNNING

        mission = Mission(
            id=mid,
            title=title,
            goal=sanitize_text(goal, 1000),
            domain=domain,
            lang=lang,
            directives=[sanitize_text(d, 500) for d in directives],
            options=dict(options),
            phases=phases,
            questions=questions,
            status=initial_status,
            workspace=mid,
        )
        mission.recalculate_progress()
        return mission


deliberator = MissionDeliberator()
