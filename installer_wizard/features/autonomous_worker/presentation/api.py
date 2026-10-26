from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse

from access import require_admin
from features.autonomous_worker.application.collab_bus import collab_bus
from features.autonomous_worker.application.deliberator import deliberator
from features.autonomous_worker.application.specialist_forge import forge
from features.autonomous_worker.domain.exceptions import MissionNotFoundError, MissionValidationError
from features.autonomous_worker.domain.models import MissionStatus, TaskStatus
from features.autonomous_worker.domain.sanitizer import sanitize_text, validate_identifier
from features.autonomous_worker.infrastructure.artifact_vault import vault
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
