from features.desktop.desk import desk
from features.projects.model import Project

WIDGET = "project_status"
KEEP_SECONDS = 3600


def key(project_id: str) -> str:
    return f"project:{project_id}"


def payload(project: Project) -> dict:
    running = next((s for s in project.steps if s.status in ("running", "waiting")), None)
    return {
        "id": project.id,
        "title": project.title,
        "status": project.status,
        "progress": project.progress,
        "total": len(project.steps),
        "done": sum(1 for s in project.steps if s.status == "done"),
        "current": running.text if running else "",
        "expert": running.expert_role if running else "",
        "error": project.error,
        "kind": project.kind,
        "model_id": project.model_id,
        "steps": [{"text": s.text, "status": s.status, "expert": s.expert_role} for s in project.steps],
    }


def push(project: Project) -> None:
    ttl = KEEP_SECONDS if project.status in ("done", "failed", "cancelled") else None
    desk.show(WIDGET, payload(project), key=key(project.id), ttl=ttl if ttl is not None else 0)


def drop(project_id: str) -> None:
    desk.hide(key=key(project_id))
