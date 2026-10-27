from features.autonomous_worker.domain.models import (
    AcceptanceCriteria,
    CollabMessage,
    Mission,
    MissionStatus,
    Phase,
    Specialist,
    Task,
    TaskStatus,
)
from features.autonomous_worker.infrastructure.artifact_vault import vault
from features.autonomous_worker.infrastructure.store import mission_store

STATUS_MAP = {
    "planning": MissionStatus.PLANNING,
    "running": MissionStatus.RUNNING,
    "paused": MissionStatus.PAUSED,
    "done": MissionStatus.DONE,
    "failed": MissionStatus.FAILED,
    "cancelled": MissionStatus.CANCELLED,
}

STEP_STATUS_MAP = {
    "pending": TaskStatus.PENDING,
    "running": TaskStatus.RUNNING,
    "review": TaskStatus.REVIEW,
    "waiting": TaskStatus.WAITING,
    "done": TaskStatus.DONE,
    "failed": TaskStatus.FAILED,
}


def sync_legacy_projects() -> None:
    try:
        from features.projects.store import projects as legacy_store
        legacy_items = legacy_store.all()
    except (ImportError, OSError, ValueError):
        return

    for proj in legacy_items:
        mid = f"proj-{proj.id}"
        existing = mission_store.find(mid)
        if existing and existing.updated_at >= proj.updated:
            continue

        tasks: list[Task] = []
        specialists_map: dict[str, Specialist] = {}

        for step in proj.steps:
            role_name = step.expert_role or "Specialista"
            exp_id = step.expert_id or f"exp_{step.id}"
            if exp_id not in specialists_map and step.expert_role:
                specialists_map[exp_id] = Specialist(
                    id=exp_id,
                    role=role_name,
                    title=role_name,
                    mission_role=role_name,
                    capabilities=[proj.kind],
                    tools=["devstudio", "workspace"],
                    is_dynamic=False,
                )

            criteria = []
            if step.acceptance:
                criteria.append(
                    AcceptanceCriteria(
                        description=step.acceptance,
                        target="Deliverable verificato",
                        verified=(step.status == "done"),
                        evidence=step.result[:160] if step.status == "done" else "",
                    )
                )

            review_notes = [step.feedback] if step.feedback else []
            tasks.append(
                Task(
                    id=step.id,
                    phase_id="p_main",
                    title=step.text,
                    description=step.text,
                    specialist_id=exp_id,
                    specialist_role=role_name,
                    depends_on=list(step.depends),
                    status=STEP_STATUS_MAP.get(step.status, TaskStatus.PENDING),
                    round=max(1, step.round + 1),
                    feedback=step.feedback,
                    criteria=criteria,
                    ceo_review_notes=review_notes,
                    result=step.result,
                    error=step.error,
                    started_at=step.started,
                    completed_at=step.finished,
                )
            )

        phase = Phase(
            id="p_main",
            title="Piano Esecutivo del Progetto",
            description=proj.goal[:280],
            tasks=tasks,
            status="done" if proj.status == "done" else "running",
        )

        collab_msgs: list[CollabMessage] = []
        for idx, entry in enumerate(proj.log):
            kind_raw = str(entry.get("kind", "message"))
            mapped_kind = (
                "approval"
                if kind_raw in ("approvato", "chiusura")
                else "rework"
                if kind_raw == "rifacimento"
                else "directive"
                if kind_raw == "direttiva"
                else "thought"
            )
            collab_msgs.append(
                CollabMessage(
                    id=f"log_{proj.id}_{idx}",
                    sender_id="ceo",
                    sender_role="CEO Project Director",
                    target_id="all",
                    channel=f"mission:{mid}",
                    content=f"[{kind_raw.upper()}] {entry.get('text', '')}",
                    kind=mapped_kind,
                    timestamp=float(entry.get("at") or proj.updated),
                )
            )

        mission = existing or Mission(
            id=mid,
            title=proj.title,
            goal=proj.goal,
            domain="3d_cad" if proj.kind == "3d" else "software",
            lang=proj.lang,
            created_at=proj.created,
        )
        mission.title = proj.title
        mission.goal = proj.goal
        mission.directives = list(proj.directives)
        mission.phases = [phase] if tasks else []
        mission.specialists = list(specialists_map.values())
        mission.collab_messages = collab_msgs
        mission.status = STATUS_MAP.get(proj.status, MissionStatus.RUNNING)
        mission.error = proj.error
        mission.workspace = proj.workspace or mid
        mission.final_review_rounds = proj.final_rounds
        mission.updated_at = proj.updated

        if proj.workspace:
            try:
                from features.devstudio import workspace as dev_ws
                ws_dir = dev_ws.project_dir(proj.workspace)
                for rel_file in dev_ws.files(ws_dir)[:40]:
                    full_p = ws_dir / rel_file
                    if full_p.is_file() and full_p.stat().st_size <= 200_000:
                        content = full_p.read_text(encoding="utf-8", errors="replace")
                        vault.store_file(
                            mission=mission,
                            relative_path=rel_file,
                            content=content,
                            generated_by="DevStudio Specialist",
                            title=full_p.name,
                        )
            except Exception:
                pass

        mission.recalculate_progress()
        mission_store.save(mission)


def forward_legacy_control(mission_id: str, action: str) -> bool:
    if not mission_id.startswith("proj-"):
        return False
    raw_pid = mission_id[5:]
    try:
        from features.projects import service as proj_service
        act_map = {
            "pause": proj_service.pause,
            "resume": proj_service.resume,
            "retry": proj_service.retry,
            "cancel": proj_service.cancel,
        }
        fn = act_map.get(action)
        if fn:
            fn(raw_pid)
            sync_legacy_projects()
            return True
    except Exception:
        return False
    return False


def forward_legacy_directive(mission_id: str, text: str) -> bool:
    if not mission_id.startswith("proj-"):
        return False
    raw_pid = mission_id[5:]
    try:
        from features.projects import management as proj_mgmt
        proj_mgmt.direct(raw_pid, text)
        sync_legacy_projects()
        return True
    except Exception:
        return False
