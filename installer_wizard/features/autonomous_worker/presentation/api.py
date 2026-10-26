from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse

from access import require_admin
from features.automations.library import library as auto_library
from features.autonomous_worker.domain.knowledge_graph import knowledge_graph
from features.autonomous_worker.application.collab_bus import collab_bus
from features.autonomous_worker.application.deliberator import deliberator
from features.autonomous_worker.application.memory_compressor import memory_compressor
from features.autonomous_worker.application.specialist_forge import forge
from features.autonomous_worker.domain.exceptions import MissionNotFoundError, MissionValidationError
from features.autonomous_worker.domain.models import MissionStatus, TaskStatus
from features.autonomous_worker.domain.sanitizer import sanitize_text, validate_identifier
from features.autonomous_worker.infrastructure.artifact_vault import vault
from features.autonomous_worker.infrastructure.llm_runtime import runtime_manager
from features.autonomous_worker.infrastructure.store import mission_store
from features.autonomous_worker.presentation.desk_notifier import notifier

router = APIRouter(prefix="/api/autonomous", tags=["autonomous"])


@router.get("/missions")
async def list_missions(_: str = Depends(require_admin)):
    return [m.to_dict() for m in mission_store.all()]


@router.post("/missions")
async def create_mission(request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "Richiesta non valida")

    goal = sanitize_text(body.get("goal"), 1000)
    if not goal or len(goal) < 3:
        raise HTTPException(400, "Obiettivo mancante o troppo breve")

    lang = sanitize_text(body.get("lang") or "it", 10)
    raw_directives = body.get("directives")
    directives = [sanitize_text(d, 500) for d in raw_directives if isinstance(d, str)] if isinstance(raw_directives, list) else []
    raw_options = body.get("options")
    options = dict(raw_options) if isinstance(raw_options, dict) else {}

    mission = await deliberator.deliberate(goal=goal, lang=lang, directives=directives, options=options)
    forge.assemble_team(mission)
    mission_store.save(mission)
    notifier.push_mission(mission)
    collab_bus.system_announce(mission, f"Nuova missione registrata: {mission.title}")
    return mission.to_dict()


@router.get("/missions/{mission_id}")
async def get_mission(mission_id: str, _: str = Depends(require_admin)):
    try:
        return mission_store.get(mission_id).to_dict()
    except MissionNotFoundError:
        raise HTTPException(404, "Missione non trovata")


@router.post("/missions/{mission_id}/control/{action}")
async def control_mission(mission_id: str, action: str, _: str = Depends(require_admin)):
    try:
        mission = mission_store.get(mission_id)
    except MissionNotFoundError:
        raise HTTPException(404, "Missione non trovata")

    act = action.lower().strip()
    if act == "pause":
        if mission.status not in (MissionStatus.RUNNING, MissionStatus.QUESTION):
            raise HTTPException(400, "Stato non valido per la pausa")
        mission.status = MissionStatus.PAUSED
        collab_bus.system_announce(mission, "Missione messa in pausa dall'amministratore.", "control")
    elif act == "resume":
        if mission.status != MissionStatus.PAUSED:
            raise HTTPException(400, "La missione non è in pausa")
        has_questions = any(not q.answered and q.options for q in mission.questions)
        mission.status = MissionStatus.QUESTION if has_questions else MissionStatus.RUNNING
        collab_bus.system_announce(mission, "Missione ripresa dall'amministratore.", "control")
    elif act == "cancel":
        mission.status = MissionStatus.CANCELLED
        collab_bus.system_announce(mission, "Missione annullata dall'amministratore.", "control")
    elif act == "retry":
        for task in mission.all_tasks():
            if task.status in (TaskStatus.FAILED, TaskStatus.WAITING):
                task.status = TaskStatus.PENDING
                task.error = ""
        mission.status = MissionStatus.RUNNING
        mission.error = ""
        collab_bus.system_announce(mission, "Riavvio dei task falliti o in attesa.", "control")
    else:
        raise HTTPException(400, f"Azione '{action}' non supportata")

    mission_store.save(mission)
    notifier.push_mission(mission)
    return mission.to_dict()


@router.post("/missions/{mission_id}/answer")
async def answer_question(mission_id: str, request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "Dati non validi")

    qid = validate_identifier(body.get("question_id", ""), "question_id")
    answer_text = sanitize_text(body.get("answer", ""), 500)
    selected = [sanitize_text(s, 120) for s in body.get("selected_options", []) if isinstance(s, str)]

    try:
        mission = mission_store.get(mission_id)
    except MissionNotFoundError:
        raise HTTPException(404, "Missione non trovata")

    question = next((q for q in mission.questions if q.id == qid), None)
    if not question:
        raise HTTPException(404, f"Domanda {qid} non trovata")

    question.answered = True
    question.answer = answer_text
    question.selected_options = selected

    collab_bus.system_announce(
        mission,
        f"Risposta dell'utente su «{question.question[:40]}...»: {answer_text or ', '.join(selected)}",
        kind="user_input",
    )

    unanswered = [q for q in mission.questions if not q.answered and q.options]
    if not unanswered and mission.status == MissionStatus.QUESTION:
        mission.status = MissionStatus.RUNNING

    mission_store.save(mission)
    notifier.push_mission(mission)
    return mission.to_dict()


@router.post("/missions/{mission_id}/directives")
async def add_directives(mission_id: str, request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "Dati non validi")

    text = sanitize_text(body.get("directive", ""), 500)
    if not text:
        raise HTTPException(400, "Direttiva vuota")

    try:
        mission = mission_store.get(mission_id)
    except MissionNotFoundError:
        raise HTTPException(404, "Missione non trovata")

    mission.directives.append(text)
    if isinstance(body.get("options"), dict):
        mission.options.update({sanitize_text(k, 50): sanitize_text(v, 200) for k, v in body["options"].items()})

    collab_bus.system_announce(mission, f"Nuova direttiva del proprietario: {text}", kind="directive")
    mission_store.save(mission)
    notifier.push_mission(mission)
    return mission.to_dict()


@router.get("/missions/{mission_id}/collab")
async def get_collab_messages(mission_id: str, limit: int = 50, _: str = Depends(require_admin)):
    try:
        mission = mission_store.get(mission_id)
        return collab_bus.recent(mission, limit=min(limit, 200))
    except MissionNotFoundError:
        raise HTTPException(404, "Missione non trovata")


@router.get("/missions/{mission_id}/artifacts")
async def list_mission_artifacts(mission_id: str, _: str = Depends(require_admin)):
    try:
        mission = mission_store.get(mission_id)
        return [a.to_dict() for a in mission.artifacts]
    except MissionNotFoundError:
        raise HTTPException(404, "Missione non trovata")


@router.get("/missions/{mission_id}/artifacts/{file_path:path}")
async def get_artifact_content(mission_id: str, file_path: str, _: str = Depends(require_admin)):
    try:
        content = vault.read_file(mission_id, file_path)
        return PlainTextResponse(content)
    except (MissionValidationError, FileNotFoundError):
        raise HTTPException(404, "Artefatto non trovato o percorso non valido")


@router.get("/runtime/config")
async def get_runtime_config(_: str = Depends(require_admin)):
    return runtime_manager.get_config()


@router.post("/runtime/config")
async def update_runtime_config(request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "Dati non validi")
    return runtime_manager.update_config(body)


@router.post("/runtime/health")
async def test_runtime_health(_: str = Depends(require_admin)):
    return await runtime_manager.check_health()


@router.get("/runtime/agents")
async def list_agent_profiles(_: str = Depends(require_admin)):
    return runtime_manager.list_agent_profiles()


@router.post("/runtime/agents")
async def save_agent_profile(request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "Dati non validi")
    agent_id = sanitize_text(body.get("agent_id"), 80)
    if not agent_id:
        raise HTTPException(400, "Identificativo agente obbligatorio")
    clean_data = {
        "agent_id": agent_id,
        "label": sanitize_text(body.get("label", ""), 100),
        "provider": sanitize_text(body.get("provider", "auto_fallback"), 30),
        "endpoint": sanitize_text(body.get("endpoint", "http://127.0.0.1:11434"), 250),
        "model": sanitize_text(body.get("model", "default"), 100),
        "temperature": float(body.get("temperature", 0.2)),
        "timeout_seconds": int(body.get("timeout_seconds", 45)),
    }
    return runtime_manager.set_agent_profile(clean_data)


@router.delete("/runtime/agents/{agent_id}")
async def delete_agent_profile(agent_id: str, _: str = Depends(require_admin)):
    sanitized_id = sanitize_text(agent_id, 80)
    deleted = runtime_manager.delete_agent_profile(sanitized_id)
    if not deleted:
        raise HTTPException(404, "Profilo agente non trovato")
    return {"status": "ok", "agent_id": sanitized_id}


@router.get("/missions/{mission_id}/memory")
async def get_mission_memory(mission_id: str, _: str = Depends(require_admin)):
    try:
        mission = mission_store.get(mission_id)
        return mission.memory.to_dict()
    except MissionNotFoundError:
        raise HTTPException(404, "Missione non trovata")


@router.post("/missions/{mission_id}/compress")
async def trigger_mission_compression(mission_id: str, _: str = Depends(require_admin)):
    try:
        mission = mission_store.get(mission_id)
    except MissionNotFoundError:
        raise HTTPException(404, "Missione non trovata")

    compressed = await memory_compressor.compress(mission)
    if compressed:
        mission_store.save(mission)
        notifier.push_mission(mission)
    return {"compressed": compressed, "memory": mission.memory.to_dict()}


@router.get("/missions/{mission_id}/automations")
async def get_mission_automations(mission_id: str, _: str = Depends(require_admin)):
    try:
        mission = mission_store.get(mission_id)
    except MissionNotFoundError:
        raise HTTPException(404, "Missione non trovata")
    return auto_library.by_mission(mission.id)


@router.post("/missions/{mission_id}/watchdog")
async def setup_mission_watchdog(mission_id: str, request: Request, _: str = Depends(require_admin)):
    try:
        mission = mission_store.get(mission_id)
    except MissionNotFoundError:
        raise HTTPException(404, "Missione non trovata")

    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "Dati non validi")

    minutes = max(1, min(1440, int(body.get("interval_minutes", 30))))
    channels = body.get("channels") or ["telegram", "display"]
    enabled = bool(body.get("enabled", True))

    existing = auto_library.by_mission(mission.id)
    watchdog = next((a for a in existing if any(act.get("type") == "mission_watchdog" for act in a.get("actions", []))), None)

    spec = {
        "name": f"Watchdog: {mission.title[:40]}",
        "description": f"Controllo periodico automatico ogni {minutes} minuti per la missione {mission.id}",
        "enabled": enabled,
        "ephemeral": True,
        "mission_id": mission.id,
        "tags": ["watchdog", "progetto"],
        "triggers": [{"type": "interval", "every": minutes, "unit": "minutes"}],
        "conditions": [],
        "actions": [{"type": "mission_watchdog", "mission_id": mission.id, "channels": channels}],
    }

    if watchdog:
        saved = auto_library.update(watchdog["id"], spec)
    else:
        saved = auto_library.add(spec, origin="watchdog_progetto")

    return saved


@router.get("/knowledge-graph")
async def get_knowledge_graph(domain: str = "all", _: str = Depends(require_admin)):
    nodes = [n.to_dict() for n in knowledge_graph.nodes.values() if domain in ("all", n.domain)]
    edges = [e.to_dict() for e in knowledge_graph.edges]
    return {"nodes": nodes, "edges": edges, "total_nodes": len(nodes), "total_edges": len(edges)}
