import time
from typing import Any
from fastapi import HTTPException

from features.autonomous_worker.application.collab_bus import collab_bus
from features.autonomous_worker.application.deliberator import deliberator
from features.autonomous_worker.application.project_bridge import (
    forward_legacy_control,
    forward_legacy_directive,
    sync_legacy_projects,
)
from features.autonomous_worker.application.specialist_forge import forge
from features.autonomous_worker.application.workspace_runtime import workspace_runtime
from features.autonomous_worker.domain.exceptions import MissionNotFoundError, MissionValidationError
from features.autonomous_worker.domain.models import MissionStatus, TaskStatus
from features.autonomous_worker.domain.sanitizer import sanitize_text, validate_identifier
from features.autonomous_worker.infrastructure.artifact_vault import vault
from features.autonomous_worker.infrastructure.store import mission_store
from features.autonomous_worker.presentation.desk_notifier import notifier


def apply_mission_control(mission_id: str, action: str) -> dict[str, Any]:
    sync_legacy_projects()
    try:
        mission = mission_store.get(mission_id)
    except MissionNotFoundError:
        raise HTTPException(404, "Missione non trovata")

    act = action.lower().strip()
    forward_legacy_control(mission_id, act)
    mission = mission_store.get(mission_id)

    if act == "pause":
        if mission.status not in (MissionStatus.RUNNING, MissionStatus.QUESTION, MissionStatus.PLANNING):
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


def apply_mission_answer(mission_id: str, body: dict[str, Any]) -> dict[str, Any]:
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
    question.answered_at = time.time()

    collab_bus.system_announce(
        mission,
        f"Risposta dell'utente su «{question.question[:60]}»: {answer_text or ', '.join(selected)}",
        kind="user_input",
    )

    unanswered = [q for q in mission.questions if not q.answered and q.options]
    if not unanswered and mission.status == MissionStatus.QUESTION:
        mission.status = MissionStatus.RUNNING

    mission_store.save(mission)
    notifier.push_mission(mission)
    return mission.to_dict()


async def apply_mission_directive(mission_id: str, body: dict[str, Any]) -> dict[str, Any]:
    text = sanitize_text(body.get("directive", ""), 500)
    if not text:
        raise HTTPException(400, "Direttiva vuota")

    sync_legacy_projects()
    try:
        mission = mission_store.get(mission_id)
    except MissionNotFoundError:
        raise HTTPException(404, "Missione non trovata")

    forward_legacy_directive(mission_id, text)
    mission = mission_store.get(mission_id)
    if text not in mission.directives:
        mission.directives.append(text)
    if isinstance(body.get("options"), dict):
        mission.options.update(
            {sanitize_text(k, 50): sanitize_text(v, 200) for k, v in body["options"].items()}
        )

    collab_bus.system_announce(mission, f"Nuova direttiva del proprietario: {text}", kind="directive")

    has_pending = any(
        t.status in (TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.REVIEW, TaskStatus.WAITING)
        for t in mission.all_tasks()
    )
    force_replan = bool(body.get("replan", False)) or not has_pending
    if force_replan and not mission_id.startswith("proj-"):
        await deliberator.replan_for_directive(mission, text)
        forge.assemble_team(mission)
        mission.status = MissionStatus.RUNNING

    mission_store.save(mission)
    notifier.push_mission(mission)
    return mission.to_dict()


def apply_mission_rollback(mission_id: str, body: dict[str, Any]) -> dict[str, Any]:
    try:
        mission = mission_store.get(mission_id)
    except MissionNotFoundError:
        raise HTTPException(404, "Missione non trovata")

    rel_path = str(body.get("file_path") or "").strip()
    target_version = int(body.get("target_version") or 1)
    if not rel_path:
        raise HTTPException(400, "file_path obbligatorio")

    try:
        artifact = vault.rollback_file(
            mission=mission,
            relative_path=rel_path,
            target_version=target_version,
            actor="Admin Rollback",
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc))
    except MissionValidationError as exc:
        raise HTTPException(400, str(exc))

    collab_bus.post(
        mission=mission,
        sender_id="admin",
        sender_role="Admin Operator",
        content=f"Rollback eseguito su «{artifact.relative_path}» alla versione v{target_version} (nuova rev v{artifact.version}).",
        kind="artifact",
        artifact_ref=artifact.relative_path,
    )
    mission_store.save(mission)
    notifier.push_mission(mission)
    return artifact.to_dict()


async def run_mission_verification(mission_id: str, body: dict[str, Any]) -> dict[str, Any]:
    try:
        mission = mission_store.get(mission_id)
    except MissionNotFoundError:
        raise HTTPException(404, "Missione non trovata")

    check_type = str(body.get("check_type") or "auto")
    entry_path = str(body.get("entry_path") or "")
    report = await workspace_runtime.verify_workspace(
        mission=mission,
        check_type=check_type,
        entry_path=entry_path,
    )
    status_label = "SUPERATA" if report["passed"] else "FALLITA"
    collab_bus.post(
        mission=mission,
        sender_id="sandbox_gate",
        sender_role="Runtime Verification Gate",
        content=f"Verifica workspace {status_label} ({', '.join(report['checks_run'])}): {report['output'][:300]}",
        kind="approval" if report["passed"] else "rework",
    )
    mission_store.save(mission)
    return report
