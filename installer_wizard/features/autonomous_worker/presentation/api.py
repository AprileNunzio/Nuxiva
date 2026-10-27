from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse

from access import require_admin, require_display
from features.automations.library import library as auto_library
from features.autonomous_worker.application.code_intel import code_intel
from features.autonomous_worker.application.collab_bus import collab_bus
from features.autonomous_worker.application.deliberator import deliberator
from features.autonomous_worker.application.memory_compressor import memory_compressor
from features.autonomous_worker.application.project_bridge import sync_legacy_projects
from features.autonomous_worker.application.specialist_forge import forge
from features.autonomous_worker.application.tool_catalog import tool_catalog
from features.autonomous_worker.domain.dag_engine import dag_resolver
from features.autonomous_worker.domain.exceptions import MissionNotFoundError, MissionValidationError
from features.autonomous_worker.domain.knowledge_graph import knowledge_graph
from features.autonomous_worker.domain.sanitizer import sanitize_text
from features.autonomous_worker.infrastructure.artifact_vault import vault
from features.autonomous_worker.infrastructure.llm_runtime import runtime_manager
from features.autonomous_worker.infrastructure.store import mission_store
from features.autonomous_worker.presentation.desk_notifier import notifier
from features.autonomous_worker.presentation.handlers import (
    apply_mission_answer,
    apply_mission_control,
    apply_mission_directive,
    apply_mission_rollback,
    run_mission_verification,
)

admin_routes = APIRouter(prefix="/api/autonomous", tags=["autonomous"])
public_routes = APIRouter(prefix="/api/autonomous", tags=["autonomous-display"])
router = admin_routes


@admin_routes.get("/missions")
async def list_missions(_: str = Depends(require_admin)):
    sync_legacy_projects()
    return [m.to_dict() for m in mission_store.all()]


@admin_routes.post("/missions")
async def create_mission(request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "Richiesta non valida")

    goal = sanitize_text(body.get("goal"), 1000)
    if not goal or len(goal) < 3:
        raise HTTPException(400, "Obiettivo mancante o troppo breve")

    lang = sanitize_text(body.get("lang") or "it", 10)
    raw_directives = body.get("directives")
    directives = (
        [sanitize_text(d, 500) for d in raw_directives if isinstance(d, str)]
        if isinstance(raw_directives, list)
        else []
    )
    raw_options = body.get("options")
    options = dict(raw_options) if isinstance(raw_options, dict) else {}

    mission = await deliberator.deliberate(goal=goal, lang=lang, directives=directives, options=options)
    forge.assemble_team(mission)
    mission_store.save(mission)
    notifier.push_mission(mission)
    collab_bus.system_announce(mission, f"Nuova missione registrata: {mission.title}")
    return mission.to_dict()


@admin_routes.get("/missions/{mission_id}")
async def get_mission(mission_id: str, _: str = Depends(require_admin)):
    sync_legacy_projects()
    try:
        return mission_store.get(mission_id).to_dict()
    except MissionNotFoundError:
        raise HTTPException(404, "Missione non trovata")


@admin_routes.post("/missions/{mission_id}/control/{action}")
async def control_mission(mission_id: str, action: str, _: str = Depends(require_admin)):
    return apply_mission_control(mission_id, action)


@public_routes.post("/missions/{mission_id}/control/{action}")
async def public_control_mission(mission_id: str, action: str, request: Request):
    require_display(request, "Solo dal display")
    return apply_mission_control(mission_id, action)


@admin_routes.post("/missions/{mission_id}/answer")
async def answer_question(mission_id: str, request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "Dati non validi")
    return apply_mission_answer(mission_id, body)


@public_routes.post("/missions/{mission_id}/answer")
async def public_answer_question(mission_id: str, request: Request):
    require_display(request, "Solo dal display")
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "Dati non validi")
    return apply_mission_answer(mission_id, body)


@admin_routes.post("/missions/{mission_id}/directives")
async def add_directives(mission_id: str, request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "Dati non validi")
    return await apply_mission_directive(mission_id, body)


@public_routes.post("/missions/{mission_id}/directives")
async def public_add_directives(mission_id: str, request: Request):
    require_display(request, "Solo dal display")
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "Dati non validi")
    return await apply_mission_directive(mission_id, body)


@admin_routes.get("/missions/{mission_id}/collab")
async def get_collab_messages(mission_id: str, limit: int = 100, _: str = Depends(require_admin)):
    try:
        mission = mission_store.get(mission_id)
        return collab_bus.recent(mission, limit=min(limit, 300))
    except MissionNotFoundError:
        raise HTTPException(404, "Missione non trovata")


@admin_routes.get("/missions/{mission_id}/artifacts")
async def list_mission_artifacts(mission_id: str, _: str = Depends(require_admin)):
    try:
        mission = mission_store.get(mission_id)
        return [a.to_dict() for a in mission.artifacts]
    except MissionNotFoundError:
        raise HTTPException(404, "Missione non trovata")


@admin_routes.get("/missions/{mission_id}/artifacts/{file_path:path}")
async def get_artifact_content(mission_id: str, file_path: str, _: str = Depends(require_admin)):
    try:
        content = vault.read_file(mission_id, file_path)
        return PlainTextResponse(content)
    except (MissionValidationError, FileNotFoundError):
        raise HTTPException(404, "Artefatto non trovato o percorso non valido")


@admin_routes.get("/missions/{mission_id}/repo-map")
async def get_mission_repo_map(mission_id: str, _: str = Depends(require_admin)):
    try:
        mission = mission_store.get(mission_id)
    except MissionNotFoundError:
        raise HTTPException(404, "Missione non trovata")
    return code_intel.export_repo_map_data(mission)


@admin_routes.post("/missions/{mission_id}/patch")
async def apply_mission_patch(mission_id: str, request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "Dati non validi")
    try:
        mission = mission_store.get(mission_id)
    except MissionNotFoundError:
        raise HTTPException(404, "Missione non trovata")

    rel_path = str(body.get("file_path") or "")
    target_block = str(body.get("target_block") or "")
    replacement_block = str(body.get("replacement_block") or "")
    expected_checksum = str(body.get("expected_checksum") or "")

    if not rel_path or not target_block:
        raise HTTPException(400, "file_path e target_block sono obbligatori")

    try:
        artifact = vault.apply_atomic_patch(
            mission=mission,
            relative_path=rel_path,
            target_block=target_block,
            replacement_block=replacement_block,
            generated_by="Admin Operator",
            expected_checksum=expected_checksum,
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc))
    except MissionValidationError as exc:
        raise HTTPException(400, str(exc))

    collab_bus.post(
        mission=mission,
        sender_id="admin",
        sender_role="Admin Operator",
        content=f"Patch atomica applicata su «{artifact.relative_path}» ({artifact.line_count} righe).",
        kind="artifact",
        artifact_ref=artifact.relative_path,
    )
    mission_store.save(mission)
    notifier.push_mission(mission)
    return artifact.to_dict()


@admin_routes.post("/missions/{mission_id}/rollback")
async def rollback_mission_artifact(mission_id: str, request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "Dati non validi")
    return apply_mission_rollback(mission_id, body)


@admin_routes.post("/missions/{mission_id}/verify")
async def verify_mission_workspace(mission_id: str, request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    return await run_mission_verification(mission_id, body)


@admin_routes.get("/runtime/config")
async def get_runtime_config(_: str = Depends(require_admin)):
    return runtime_manager.get_config()


@admin_routes.post("/runtime/config")
async def update_runtime_config(request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "Dati non validi")
    return runtime_manager.update_config(body)


@admin_routes.post("/runtime/health")
async def test_runtime_health(_: str = Depends(require_admin)):
    return await runtime_manager.check_health()


@admin_routes.get("/runtime/agents")
async def list_agent_profiles(_: str = Depends(require_admin)):
    return runtime_manager.list_agent_profiles()


@admin_routes.post("/runtime/agents")
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


@admin_routes.delete("/runtime/agents/{agent_id}")
async def delete_agent_profile(agent_id: str, _: str = Depends(require_admin)):
    sanitized_id = sanitize_text(agent_id, 80)
    deleted = runtime_manager.delete_agent_profile(sanitized_id)
    if not deleted:
        raise HTTPException(404, "Profilo agente non trovato")
    return {"status": "ok", "agent_id": sanitized_id}


@admin_routes.get("/missions/{mission_id}/memory")
async def get_mission_memory(mission_id: str, _: str = Depends(require_admin)):
    try:
        mission = mission_store.get(mission_id)
        return mission.memory.to_dict()
    except MissionNotFoundError:
        raise HTTPException(404, "Missione non trovata")


@admin_routes.post("/missions/{mission_id}/compress")
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


@admin_routes.get("/missions/{mission_id}/automations")
async def get_mission_automations(mission_id: str, _: str = Depends(require_admin)):
    try:
        mission = mission_store.get(mission_id)
    except MissionNotFoundError:
        raise HTTPException(404, "Missione non trovata")
    return auto_library.by_mission(mission.id)


@admin_routes.post("/missions/{mission_id}/watchdog")
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
    watchdog = next(
        (a for a in existing if any(act.get("type") == "mission_watchdog" for act in a.get("actions", []))),
        None,
    )

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


@admin_routes.get("/knowledge-graph")
async def get_knowledge_graph(domain: str = "all", _: str = Depends(require_admin)):
    nodes = [n.to_dict() for n in knowledge_graph.nodes.values() if domain in ("all", n.domain)]
    edges = [e.to_dict() for e in knowledge_graph.edges]
    return {"nodes": nodes, "edges": edges, "total_nodes": len(nodes), "total_edges": len(edges)}


@admin_routes.get("/missions/{mission_id}/dag")
async def get_mission_dag(mission_id: str, _: str = Depends(require_admin)):
    try:
        mission = mission_store.get(mission_id)
    except MissionNotFoundError:
        raise HTTPException(404, "Missione non trovata")
    return dag_resolver.export_graph_data(mission.phases)


@admin_routes.get("/tools")
async def get_tool_catalog(_: str = Depends(require_admin)):
    return tool_catalog.scan_all_tools()


@admin_routes.post("/tools/scan")
async def scan_tools_now(_: str = Depends(require_admin)):
    return tool_catalog.scan_all_tools(force_refresh=True)


@admin_routes.post("/tools/study")
async def study_and_forge(request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "Dati non validi")
    try:
        res = await tool_catalog.study_and_forge_tool(body)
        return res
    except ValueError as exc:
        raise HTTPException(400, str(exc))
