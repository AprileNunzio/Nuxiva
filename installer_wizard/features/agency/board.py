from features.agency import service
from features.agency.forge.registry import registry
from features.agency.text import clean

COUNTS = ("total", "pending", "running", "review", "done", "failed", "cancelled", "blocked")
TASK_FIELDS = ("id", "title", "role", "status", "attempts")
MAX_TASKS = 400
MAX_QUESTIONS = 8


def _number(value) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def card(summary: dict) -> dict:
    project = summary.get("project") or {}
    progress = summary.get("progress") or {}
    usage = project.get("usage") or {}
    budget = project.get("budget") or {}
    return {
        "id": str(project.get("id", "")),
        "title": clean(project.get("title"), 120),
        "status": str(project.get("status", "")),
        "percent": min(100, _number(progress.get("percent"))),
        "counts": {key: _number(progress.get(key)) for key in COUNTS},
        "tokens": _number(usage.get("tokens")),
        "seconds": _number(usage.get("seconds")),
        "budget_tokens": _number(budget.get("tokens")),
        "eta_seconds": _number(summary.get("critical_path_seconds")),
        "created_at_ms": _number(project.get("created_at_ms")),
    }


def _task(raw: dict) -> dict:
    task = {key: raw.get(key) for key in TASK_FIELDS}
    task["title"] = clean(task["title"], 160)
    task["attempts"] = _number(task["attempts"])
    task["depends_on"] = [str(d) for d in raw.get("depends_on", [])][:40]
    return task


def _questions(reasoning) -> list[dict]:
    exchanges = (reasoning or {}).get("exchanges") or []
    return [{"q": clean(e.get("question"), 300), "a": clean(e.get("answer"), 400)}
            for e in exchanges[:MAX_QUESTIONS] if isinstance(e, dict)]


async def overview() -> dict:
    data = await service.overview()
    capacity = data.get("capacity") or {}
    limit = capacity.get("capacity") or {}
    cards = sorted((card(p) for p in data.get("projects") or []), key=lambda c: -c["created_at_ms"])
    return {
        "agents": {"running": _number(capacity.get("running")), "parallel": _number(limit.get("parallel_agents"))},
        "tools": len(registry.active()),
        "projects": cards,
    }


async def focus(project_id: str) -> dict:
    data = await service.detail(project_id)
    blueprint = data.get("blueprint") or {}
    reasoning = data.get("reasoning") or {}
    return {
        **card(data),
        "goal": clean((data.get("project") or {}).get("goal"), 400),
        "summary": clean(blueprint.get("summary"), 600),
        "roles": [{"id": str(r.get("id", "")), "mission": clean(r.get("mission"), 200)}
                  for r in blueprint.get("roles") or [] if isinstance(r, dict)][:24],
        "tasks": [_task(t) for t in (data.get("tasks") or [])[:MAX_TASKS] if isinstance(t, dict)],
        "questions": _questions(reasoning),
        "issues": [clean(i, 300) for i in (reasoning.get("issues") or [])[:MAX_QUESTIONS]],
        "tools": [t.call_name for t in registry.all() if t.origin.get("project") == project_id],
    }
