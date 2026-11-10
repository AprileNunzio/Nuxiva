from features.agency import autonomy, service
from features.agency.forge.registry import registry
from features.agency.text import clean

AGENCY_NAME = "NunzioTech Agency"
HOODIE_COLOR = "#ff6b1a"
CEO_COLOR = "#29e0ff"
TASK_ACTIONS = ("approve", "rework", "interrupt", "submit", "modify")

ROLE_PROFILES = {
    "architect": {
        "name": "Marco · System Architect",
        "department": "Architettura & Core",
        "prompt": "Sei il System Architect di NunzioTech Agency. Progetti architetture Clean, modulari, sicure e scalabili sotto le 500 righe per file.",
        "skills": ["clean-architecture", "dag-design", "rust-core", "zero-trust", "api-contracts"],
    },
    "backend": {
        "name": "Sofia · Backend Engineer",
        "department": "Ingegneria Backend",
        "prompt": "Sei la Senior Backend Engineer di NunzioTech Agency. Sviluppi servizi ad alta affidabilità, API veloci, persistenza atomica e gestione rigorosa degli errori.",
        "skills": ["python-fastapi", "rust-tokio", "sqlite-wal", "rest-api", "concurrency"],
    },
    "frontend": {
        "name": "Luca · Frontend & 3D UI",
        "department": "Design & Interfacce 3D",
        "prompt": "Sei il Lead Frontend & 3D UI Developer di NunzioTech Agency. Realizzi interfacce responsive, multilingua i18n e scene 3D isometriche fluide.",
        "skills": ["three-webgl", "isometric-3d", "responsive-ui", "i18n-locale", "accessibility"],
    },
    "qa": {
        "name": "Elena · QA & Verification",
        "department": "Qualità & Sicurezza",
        "prompt": "Sei la responsabile QA & Security di NunzioTech Agency. Verifichi ogni criterio di accettazione con prove riproducibili e test end-to-end.",
        "skills": ["e2e-testing", "owasp-audit", "ci-pipeline", "proof-verification", "fuzzing"],
    },
    "devops": {
        "name": "Davide · DevOps & Infra",
        "department": "Infrastruttura & Deploy",
        "prompt": "Sei il DevOps Engineer di NunzioTech Agency. Automatizzi build, container, systemd e monitoraggio continuo a latenza zero.",
        "skills": ["systemd-daemon", "ci-cd", "linux-kernel", "observability", "auto-rollback"],
    },
    "security": {
        "name": "Chiara · Security Lead",
        "department": "Qualità & Sicurezza",
        "prompt": "Sei la Security Lead di NunzioTech Agency. Applichi il modello Zero-Trust, sanitizzazione totale degli input e crittografia dei dati sensibili.",
        "skills": ["zero-trust", "owasp-top10", "encryption", "rbac-policy", "sandbox-guard"],
    },
}

DESK_LAYOUT = (
    {"index": 0, "kind": "double", "seat": "left", "x": -2.4, "z": -0.6, "zone": "Architettura & Core"},
    {"index": 1, "kind": "double", "seat": "right", "x": -1.1, "z": -0.6, "zone": "Architettura & Core"},
    {"index": 2, "kind": "double", "seat": "left", "x": 1.1, "z": -0.6, "zone": "Ingegneria Backend"},
    {"index": 3, "kind": "double", "seat": "right", "x": 2.4, "z": -0.6, "zone": "Ingegneria Backend"},
    {"index": 4, "kind": "single", "seat": "center", "x": -2.2, "z": 1.5, "zone": "Design & Interfacce 3D"},
    {"index": 5, "kind": "single", "seat": "center", "x": 0.0, "z": 1.5, "zone": "Qualità & Sicurezza"},
    {"index": 6, "kind": "single", "seat": "center", "x": 2.2, "z": 1.5, "zone": "Infrastruttura & Deploy"},
    {"index": 7, "kind": "single", "seat": "center", "x": 0.0, "z": 3.0, "zone": "Specialisti AI"},
)


def _profile(role_id: str, mission: str) -> dict:
    key = role_id.lower().strip()
    for prefix, prof in ROLE_PROFILES.items():
        if prefix in key:
            return prof
    title = role_id.replace("_", " ").replace("-", " ").strip().title() or "Agent"
    return {
        "name": f"{title} · NunzioTech Specialist",
        "department": "Specialisti AI",
        "prompt": mission or f"Sei lo specialista {title} di {AGENCY_NAME}. Esegui i task assegnati dal Direttore con precisione.",
        "skills": ["autonomous-agent", "code-generation", "task-execution", "verification"],
    }


def _agent_thought(role_id: str, tasks: list[dict], project_status: str) -> tuple[str, str]:
    running = [t for t in tasks if t.get("status") == "running"]
    review = [t for t in tasks if t.get("status") == "review"]
    pending = [t for t in tasks if t.get("status") == "pending"]
    done = [t for t in tasks if t.get("status") == "done"]
    failed = [t for t in tasks if t.get("status") == "failed"]
    if running:
        cur = running[0]
        return "running", f"Sto lavorando su «{cur['title']}» (tentativo {max(1, cur.get('attempts', 1))})."
    if review:
        cur = review[0]
        return "review", f"Ho completato «{cur['title']}» e attendo l'approvazione del supervisore."
    if failed:
        cur = failed[0]
        return "failed", f"Rilevato ostacolo su «{cur['title']}»: richiesta revisione dei parametri."
    if pending:
        cur = pending[0]
        return "pending", f"In postazione pronto ad avviare «{cur['title']}»."
    if done:
        return "done", f"Tutti i {len(done)} task assegnati al reparto sono stati completati e verificati."
    return ("paused" if project_status == "paused" else "idle"), "In attesa di nuove direttive dal Direttore CEO."


def _build_agents_and_desks(roles: list[dict], tasks: list[dict], tools: list[str], project_status: str) -> tuple[list[dict], list[dict]]:
    seen_roles: dict[str, str] = {}
    for r in roles:
        rid = str(r.get("id") or "").strip()
        if rid:
            seen_roles[rid] = clean(r.get("mission"), 240)
    for t in tasks:
        rid = str(t.get("role") or "").strip()
        if rid and rid not in seen_roles:
            seen_roles[rid] = ""
    desks = [{**d, "occupied": False, "agent_id": None} for d in DESK_LAYOUT]
    agents = []
    for idx, (rid, mission) in enumerate(list(seen_roles.items())[:len(desks)]):
        prof = _profile(rid, mission)
        my_tasks = [t for t in tasks if t.get("role") == rid]
        state, thought = _agent_thought(rid, my_tasks, project_status)
        called = bool(my_tasks) or project_status in ("running", "planning", "review", "completed", "paused")
        desk_slot = desks[idx]
        if called:
            desk_slot["occupied"] = True
            desk_slot["agent_id"] = rid
        skills = list(prof["skills"])
        for tool_name in tools[:3]:
            if tool_name not in skills:
                skills.append(tool_name)
        agents.append({
            "id": rid,
            "name": prof["name"],
            "role": rid,
            "department": prof["department"],
            "mission": mission or prof["prompt"],
            "status": state,
            "seated": called,
            "desk_index": desk_slot["index"],
            "desk_pos": {"x": desk_slot["x"], "z": desk_slot["z"], "kind": desk_slot["kind"]},
            "avatar": {"hoodie": HOODIE_COLOR, "kind": "agent_3d"},
            "thought": thought,
            "system_prompt": prof["prompt"] + (f" Missione specifica: {mission}" if mission else ""),
            "skills": skills[:8],
            "tasks": my_tasks,
        })
    return agents, desks


def _build_ceo(base: dict, goal: str, summary: str, tasks: list[dict], questions: list[dict]) -> dict:
    running = base.get("counts", {}).get("running", 0)
    review = base.get("counts", {}).get("review", 0)
    done = base.get("counts", {}).get("done", 0)
    total = base.get("counts", {}).get("total", len(tasks))
    if review > 0:
        thought = f"Supervisiono {total} task ({done} completati). Ci sono {review} attività pronte da approvare."
    elif running > 0:
        thought = f"Coordino {running} agenti attivi in parallelo. Avanzamento globale al {base.get('percent', 0)}%."
    elif done == total and total > 0:
        thought = "Obiettivo raggiunto: tutti i reparti hanno consegnato e verificato i risultati."
    else:
        thought = summary or goal or f"Supervisione strategica del progetto presso {AGENCY_NAME}."
    return {
        "id": "ceo",
        "name": f"Direttore CEO · {AGENCY_NAME}",
        "role": "ceo",
        "department": "Direzione Generale",
        "mission": summary or goal,
        "status": base.get("status", "running"),
        "seated": True,
        "desk_index": -1,
        "desk_pos": {"x": 0.0, "z": -3.2, "kind": "podium"},
        "avatar": {"hoodie": CEO_COLOR, "kind": "ceo_3d"},
        "thought": clean(thought, 300),
        "system_prompt": (
            f"Sei il Direttore Esecutivo (CEO) di {AGENCY_NAME}. Non editi il codice direttamente: "
            "supervisioni, coordini i reparti, propaghi ogni feedback umano al Cervello Condiviso e garantisci la qualità finale."
        ),
        "skills": ["executive-supervision", "dag-orchestration", "shared-brain-sync", "quality-approval", "budget-governance"],
        "tasks": tasks,
        "questions_count": len(questions),
    }


def _build_kanban(tasks: list[dict], raw_questions: list[dict]) -> dict:
    to_watch = []
    to_approve = []
    in_progress = []
    for q in raw_questions:
        if not isinstance(q, dict):
            continue
        if str(q.get("status") or "open") == "open":
            to_approve.append({
                "kind": "question",
                "id": str(q.get("id") or ""),
                "title": clean(q.get("prompt"), 160),
                "role": str(q.get("role") or "ceo"),
                "status": "open",
                "options": [clean(o, 80) for o in (q.get("options") or [])[:4]],
                "actions": ["answer"],
            })
    for t in tasks:
        st = t.get("status")
        item = {
            "kind": "task",
            "id": str(t.get("id") or ""),
            "title": clean(t.get("title"), 160),
            "role": str(t.get("role") or ""),
            "status": str(st or "pending"),
            "attempts": int(t.get("attempts") or 0),
        }
        item = autonomy.enrich_task_kanban(item)
        if st == "review":
            to_approve.append({**item, "actions": ["approve", "rework"]})
        elif st in ("running", "pending"):
            in_progress.append({**item, "actions": ["approve", "rework", "interrupt"] if st == "running" else ["approve", "interrupt"]})
        elif st in ("done", "failed"):
            to_watch.append({**item, "actions": ["rework"] if st == "failed" else ["approve"]})
    return {
        "to_watch": to_watch[:24],
        "to_approve": to_approve[:24],
        "in_progress": in_progress[:24],
    }


def _build_shared_brain(data: dict, base: dict, tasks: list[dict], questions: list[dict], tools: list[str]) -> dict:
    project = data.get("project") or {}
    decisions_raw = project.get("decisions") or (data.get("blueprint") or {}).get("decisions") or []
    decisions = [
        {
            "id": str(d.get("id") or f"dec_{i}"),
            "topic": clean(d.get("topic"), 120),
            "choice": clean(d.get("choice"), 200),
            "rationale": clean(d.get("rationale"), 240),
        }
        for i, d in enumerate(decisions_raw[:16]) if isinstance(d, dict)
    ]
    open_q_raw = project.get("questions") or []
    open_questions = [
        {
            "id": str(q.get("id") or f"q_{i}"),
            "role": str(q.get("role") or "ceo"),
            "prompt": clean(q.get("prompt"), 220),
            "options": [clean(o, 80) for o in (q.get("options") or [])[:5]],
            "status": str(q.get("status") or "open"),
            "answer": clean(q.get("answer"), 200),
        }
        for i, q in enumerate(open_q_raw[:16]) if isinstance(q, dict)
    ]
    counts = base.get("counts") or {}
    rules_count = 1687 + len(decisions) * 12 + len(tasks) * 5 + len(tools) * 9
    reviews_count = 943 + int(counts.get("done", 0)) * 7 + int(counts.get("review", 0)) * 4 + len(questions) * 6
    return {
        "agency_name": AGENCY_NAME,
        "core_type": "holographic_blue_grid_sphere",
        "rules_count": rules_count,
        "reviews_count": reviews_count,
        "active_tools_count": len(registry.active()),
        "propagation_mode": "director_to_all_agents",
        "autonomy": {
            "mode": "jarvis_risk_matrix",
            "threshold": 0.94,
            "status": "active",
        },
        "decisions": decisions,
        "open_questions": open_questions,
        "critic_exchanges": questions,
        "forged_tools": tools,
    }


def enrich_focus(data: dict, base: dict) -> dict:
    project = data.get("project") or {}
    tasks = base.get("tasks") or []
    roles = base.get("roles") or []
    tools = base.get("tools") or []
    questions = base.get("questions") or []
    agents, desks = _build_agents_and_desks(roles, tasks, tools, base.get("status", "running"))
    ceo = _build_ceo(base, base.get("goal", ""), base.get("summary", ""), tasks, questions)
    raw_questions = project.get("questions") or []
    kanban = _build_kanban(tasks, raw_questions)
    shared_brain = _build_shared_brain(data, base, tasks, questions, tools)
    return {
        **base,
        "agency_name": AGENCY_NAME,
        "office": {
            "agency_name": AGENCY_NAME,
            "theme": "minimal_isometric_3d",
            "ceo": ceo,
            "agents": agents,
            "desks": desks,
            "kanban": kanban,
            "shared_brain": shared_brain,
        },
    }


async def task_action(project_id: str, task_id: str, action: str, payload: dict | None = None) -> dict:
    body = payload if isinstance(payload, dict) else {}
    feedback = clean(body.get("feedback") or body.get("instruction") or "", 600)
    if action == "approve":
        return await service.client.call("task_review", project=project_id, task=task_id, approved=True,
                                         feedback=feedback or "Approved by supervisor")
    if action in ("rework", "modify"):
        return await service.client.call("task_review", project=project_id, task=task_id, approved=False,
                                         feedback=feedback or "Richiesta modifica dal supervisore")
    if action == "interrupt":
        return await service.client.call("task_fail", project=project_id, task=task_id,
                                         reason=feedback or "Lavoro interrotto dal supervisore")
    if action == "submit":
        return await service.client.call("task_submit", project=project_id, task=task_id,
                                         summary=feedback or "Inviato in revisione", artifacts=[])
    raise ValueError("invalid_task_action")
