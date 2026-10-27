import time

STATE_OF = {
    "planning": "running",
    "question": "running",
    "running": "running",
    "paused": "paused",
    "done": "done",
    "failed": "error",
    "cancelled": "cancelled",
}
STEP_OF = {
    "pending": "pending",
    "waiting": "pending",
    "running": "running",
    "review": "running",
    "done": "done",
    "failed": "error",
}
RECENT = 7 * 86400


def projects() -> list[dict]:
    rows: list[dict] = []
    now = time.time()
    seen_ids: set[str] = set()

    try:
        from features.autonomous_worker.infrastructure.store import mission_store
        missions = mission_store.all()
    except (ImportError, OSError, ValueError):
        missions = []

    for m in missions:
        raw_status = m.status.value if hasattr(m.status, "value") else str(m.status)
        state = STATE_OF.get(raw_status, "running")
        stamp = m.updated_at or m.created_at
        if state in ("done", "error", "cancelled") and now - stamp > RECENT:
            continue
        all_t = m.all_tasks()
        current = next(
            (t for t in all_t if (t.status.value if hasattr(t.status, "value") else str(t.status)) in ("running", "review")),
            None,
        )
        rows.append({
            "id": f"mission:{m.id}",
            "kind": "project",
            "title": m.title,
            "feature": "autonomous_worker",
            "ref": m.id,
            "state": state,
            "stage": current.title[:120] if current else "",
            "detail": m.goal[:200],
            "progress": m.progress / 100,
            "summary": f"{len(m.artifacts)} deliverable",
            "error": m.error[:200],
            "created": m.created_at,
            "updated": stamp,
            "finished": stamp if state in ("done", "error", "cancelled") else 0.0,
            "result": {"app": "autonomous_worker", "payload": {"missionId": m.id}},
            "offer": None,
            "answered": True,
            "steps": [
                {
                    "text": t.title[:120],
                    "state": STEP_OF.get(t.status.value if hasattr(t.status, "value") else str(t.status), "pending"),
                }
                for t in all_t[:40]
            ],
        })
        if m.id.startswith("proj-"):
            seen_ids.add(m.id[5:])

    try:
        from features.projects.store import projects as store
        items = store.all()
    except (ImportError, OSError, ValueError):
        items = []

    for p in items:
        if p.id in seen_ids:
            continue
        state = STATE_OF.get(p.status, "running")
        stamp = max([p.created, *[s.finished for s in p.steps if s.finished]] or [p.created])
        if state in ("done", "error", "cancelled") and now - stamp > RECENT:
            continue
        current = next((s for s in p.steps if s.status in ("running", "review")), None)
        rows.append({
            "id": f"project:{p.id}",
            "kind": "project",
            "title": p.title,
            "feature": "projects",
            "ref": p.id,
            "state": state,
            "stage": current.text[:120] if current else "",
            "detail": p.goal[:200],
            "progress": p.progress / 100,
            "summary": "",
            "error": p.error[:200],
            "created": p.created,
            "updated": stamp,
            "finished": stamp if state in ("done", "error", "cancelled") else 0.0,
            "result": {"app": "autonomous_worker", "payload": {"missionId": f"proj-{p.id}"}},
            "offer": None,
            "answered": True,
            "steps": [{"text": s.text[:120], "state": STEP_OF.get(s.status, "pending")} for s in p.steps[:40]],
        })
    return rows
