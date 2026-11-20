from agenti.agency import autonomy, proactive, service
from agenti.agency.forge.registry import registry
from agenti.agency.text import clean

AGENCY_NAME = "NunzioTech Agency"
HOODIE_COLOR = "#ff6b1a"
CEO_COLOR = "#29e0ff"
TASK_ACTIONS = ("approve", "rework", "interrupt", "submit", "modify")

from agenti.agency import circadian
from agenti.agency.scanner import department_scanner
from agenti.agency.tools_catalog import automations


class DynamicRoleProfiles(dict):
    def _deps(self) -> dict:
        return department_scanner.scan_departments()

    def __getitem__(self, key):
        deps = self._deps()
        if key in deps:
            return deps[key]
        return super().__getitem__(key)

    def __contains__(self, key):
        deps = self._deps()
        return key in deps or super().__contains__(key)

    def get(self, key, default=None):
        deps = self._deps()
        return deps.get(key, super().get(key, default))

    def items(self):
        return self._deps().items()

    def values(self):
        return self._deps().values()

    def keys(self):
        return self._deps().keys()


ROLE_PROFILES = DynamicRoleProfiles()

DESK_LAYOUT = (
    {"index": 0, "kind": "double", "seat": "left", "x": -2.4, "z": -0.6, "zone": "Architettura & Core"},
    {"index": 1, "kind": "double", "seat": "right", "x": -1.1, "z": -0.6, "zone": "Architettura & Core"},
    {"index": 2, "kind": "double", "seat": "left", "x": 1.1, "z": -0.6, "zone": "Ingegneria Backend"},
    {"index": 3, "kind": "double", "seat": "right", "x": 2.4, "z": -0.6, "zone": "Ingegneria Backend"},
    {"index": 4, "kind": "single", "seat": "center", "x": -2.2, "z": 1.5, "zone": "Design & Interfacce 3D"},
    {"index": 5, "kind": "single", "seat": "center", "x": 0.0, "z": 1.5, "zone": "Qualità & Sicurezza"},
    {"index": 6, "kind": "single", "seat": "center", "x": 2.2, "z": 1.5, "zone": "Infrastruttura & Deploy"},
    {"index": 7, "kind": "single", "seat": "center", "x": -2.2, "z": 3.0, "zone": "Customer Care & Fonia"},
    {"index": 8, "kind": "single", "seat": "center", "x": -0.7, "z": 3.0, "zone": "Amministrazione & Fisco"},
    {"index": 9, "kind": "single", "seat": "center", "x": 0.7, "z": 3.0, "zone": "Commerciale & Vendite"},
    {"index": 10, "kind": "single", "seat": "center", "x": 2.2, "z": 3.0, "zone": "Integrazioni & MCP"},
    {"index": 11, "kind": "single", "seat": "center", "x": 0.0, "z": 4.2, "zone": "Specialisti AI"},
)


def _profile(role_id: str, mission: str) -> dict:
    key = role_id.lower().strip()
    departments = department_scanner.scan_departments()
    for prefix, prof in departments.items():
        if prefix in key or key in prefix:
            return prof
    found = department_scanner.find_specialist(f"{role_id} {mission}")
    if found is not None:
        return found
    title = role_id.replace("_", " ").replace("-", " ").strip().title() or "Specialist"
    return {
        "id": role_id,
        "name": f"{title} · Specialist",
        "department": f"Dipartimento {title}",
        "prompt": mission or f"Sei lo specialista {role_id} di {AGENCY_NAME}. Esegui i compiti assegnati con precisione.",
        "skills": ["autonomous-specialist", "task-execution", "compliance", "verification"],
        "capabilities": ["domain_task", "data_synthesis"],
        "widgets": [{"id": f"{role_id}_dashboard", "type": "domain_card", "title": f"Monitor {title}"}],
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
    extra_needed = len(seen_roles) - len(desks)
    for i in range(max(0, extra_needed)):
        idx = len(desks)
        row = (idx - 12) // 4 + 1
        col = (idx - 12) % 4
        x = -2.2 + col * 1.45
        z = 4.2 + row * 1.4
        desks.append({
            "index": idx,
            "kind": "single",
            "seat": "center",
            "x": round(x, 2),
            "z": round(z, 2),
            "zone": "Reparti Specializzati Dinamici",
            "occupied": False,
            "agent_id": None,
        })
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
            "widgets": prof.get("widgets", []),
            "capabilities": prof.get("capabilities", []),
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
            f"Sei il Direttore Esecutivo (CEO) di {AGENCY_NAME}. Dirigi e coordini l'intera operatività aziendale: "
            "ascolti tutti i canali in ingresso (WhatsApp, Twilio, Email, Fatture SDI), valuti se creare automazioni persistenti "
            "per inneschi temporali o eventi, verifichi se i reparti specialisti necessari esistono (altrimenti ne forgi subito di nuovi indipendenti), "
            "avvii cicli interattivi domanda/risposta in qualsiasi lingua quando mancano dettagli e supervisioni l'esecuzione a zero allucinazioni."
        ),
        "skills": [
            "executive-supervision",
            "omnichannel-dispatching",
            "dag-orchestration",
            "preflight-governance",
            "budget-oversight",
            "shared-brain-sync",
            "invoice-compliance",
            "enterprise-mcp",
            "dynamic-department-forge",
            "event-automation-evaluation",
            "interactive-clarification-loop",
        ],
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
    telemetry = proactive.sample_telemetry()
    insights = proactive.analyze_insights(tasks, open_questions, telemetry)
    title = project.get("title") or "Progetto"
    briefing = proactive.generate_briefing("it", title, counts, insights)
    return {
        "agency_name": AGENCY_NAME,
        "core_type": "holographic_blue_grid_sphere",
        "rules_count": rules_count,
        "reviews_count": reviews_count,
        "active_tools_count": len(registry.active()),
        "propagation_mode": "director_to_all_agents",
        "autonomy": {
            "mode": "nuxiva_risk_matrix",
            "threshold": 0.94,
            "status": "active",
        },
        "telemetry": telemetry.to_dict(),
        "proactive_insights": [ins.to_dict() for ins in insights],
        "briefing": briefing,
        "decisions": decisions,
        "open_questions": open_questions,
        "critic_exchanges": questions,
        "forged_tools": tools,
    }


UNIVERSAL_WIDGETS = [
    {
        "id": "widget_universal_presence_clock",
        "type": "presence_clock_orb",
        "title": "Presenza & Ritmo Circadiano",
        "style": "borderless_glassmorphic",
        "visual": {"border": "none", "background": "transparent", "glow": "rgba(255, 255, 255, 0.15)"},
    },
    {
        "id": "widget_universal_voice_orb",
        "type": "holographic_voice_orb",
        "title": "Interfaccia Vocale Full-Duplex & Barge-In",
        "style": "borderless_glassmorphic",
        "visual": {"border": "none", "background": "transparent", "glow": "cyan", "waveform": True},
    },
    {
        "id": "widget_universal_automations_pill",
        "type": "floating_automations_strip",
        "title": "Flussi e Automazioni Attive",
        "style": "borderless_glassmorphic",
        "visual": {"border": "none", "background": "transparent", "pills": True},
    },
]


def _build_contextual_widgets(data: dict, base: dict, agents: list[dict]) -> list[dict]:
    activity = str(data.get("current_activity") or base.get("goal") or "").lower()
    widgets = []
    if any(k in activity for k in ("cucin", "forno", "ricett", "timer", "piatto")):
        widgets.append({
            "id": "contextual_cooking_timer",
            "type": "floating_cooking_timer",
            "title": "Timer di Cottura Attivo",
            "style": "borderless_glassmorphic",
            "visual": {"border": "none", "background": "transparent", "glow": "amber", "radial_progress": True},
            "remaining_seconds": 720,
        })
    if any(k in activity for k in ("compit", "studio", "scuola", "matematica", "tutor")):
        widgets.append({
            "id": "contextual_socratic_canvas",
            "type": "socratic_thinking_canvas",
            "title": "Lavagna Maieutica & Passi Guidati",
            "style": "borderless_glassmorphic",
            "visual": {"border": "none", "background": "transparent", "glow": "cyan", "interactive_graph": True},
        })
    if any(k in activity for k in ("favol", "fiaba", "nanna", "bambin", "racconto")):
        widgets.append({
            "id": "contextual_dreamscape_player",
            "type": "storyteller_dreamscape",
            "title": "Fiaba in Corso & Onde Rilassanti",
            "style": "borderless_glassmorphic",
            "visual": {"border": "none", "background": "transparent", "glow": "indigo", "floating_text": True},
        })
    return widgets


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
    active_person = data.get("active_person") or base.get("active_person")
    co_present = data.get("co_present_slugs") or base.get("co_present_slugs") or []
    contextual_w = _build_contextual_widgets(data, base, agents)
    dept_widgets = [
        {**w, "style": "borderless_glassmorphic", "visual": {"border": "none", "background": "transparent"}}
        for a in agents for w in a.get("widgets", [])
    ]
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
            "active_automations": automations.get_active_automations(),
            "department_widgets": dept_widgets,
            "universal_widgets": UNIVERSAL_WIDGETS,
            "contextual_active_widgets": contextual_w,
            "active_person": active_person,
            "co_present_slugs": co_present,
            "circadian_context": circadian.resolve_circadian_context(person_slug=active_person, co_present_slugs=co_present),
        },
    }


async def task_action(project_id: str, task_id: str, action: str, payload: dict | None = None) -> dict:
    body = payload if isinstance(payload, dict) else {}
    feedback = clean(body.get("feedback") or body.get("instruction") or "", 600)
    mapped = "rework" if action == "modify" else action
    if mapped not in ("approve", "rework", "interrupt", "submit"):
        raise ValueError("invalid_task_action")
    return await service.review(project_id, task_id, mapped, feedback or ("Richiesta modifica dal supervisore" if mapped == "rework" else ""))
