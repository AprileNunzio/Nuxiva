import time

STATE_OF = {"planning": "running", "running": "running", "paused": "paused", "done": "done", "failed": "error", "cancelled": "cancelled"}
STEP_OF = {"pending": "pending", "waiting": "pending", "running": "running", "review": "running", "done": "done", "failed": "error"}
RECENT = 7 * 86400


def projects() -> list[dict]:
    try:
        from features.projects.store import projects as store
        items = store.all()
    except (ImportError, OSError, ValueError):
        return []
    rows = []
    now = time.time()
    for p in items:
        state = STATE_OF.get(p.status, "running")
        stamp = max([p.created, *[s.finished for s in p.steps if s.finished]] or [p.created])
        if state in ("done", "error", "cancelled") and now - stamp > RECENT:
            continue
        current = next((s for s in p.steps if s.status in ("running", "review")), None)
        rows.append({"id": f"project:{p.id}", "kind": "project", "title": p.title, "feature": "projects", "ref": p.id, "state": state, "stage": current.text[:120] if current else "",
                     "detail": p.goal[:200], "progress": p.progress / 100, "summary": "", "error": p.error[:200], "created": p.created, "updated": stamp, "finished": stamp if state in ("done", "error", "cancelled") else 0.0,
                     "result": {"app": "projects", "payload": {"project": p.id}} if state == "done" else {}, "offer": None, "answered": True,
                     "steps": [{"text": s.text[:120], "state": STEP_OF.get(s.status, "pending")} for s in p.steps[:40]]})
    return rows
