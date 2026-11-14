from agenti.team.graph import graph
from agenti.team.swarm import swarm

MAX_STEPS = 24
MAX_TEXT = 160


def _text(value) -> str:
    return "".join(ch for ch in str(value if value is not None else "") if ch.isprintable())[:MAX_TEXT]


def _rows(source, keys: tuple[str, ...]) -> list[dict]:
    rows = source if isinstance(source, list) else []
    return [{k: _text(row.get(k)) for k in keys} for row in rows[:MAX_STEPS] if isinstance(row, dict)]


def plan() -> dict | None:
    last = swarm.last_plan
    if not isinstance(last, dict):
        return None
    plan_doc = last.get("plan") if isinstance(last.get("plan"), dict) else {}
    report = last.get("report") if isinstance(last.get("report"), dict) else {}
    outcomes = {str(s.get("step")): _text(s.get("outcome")) for s in report.get("steps", []) if isinstance(s, dict)}
    steps = _rows(plan_doc.get("steps"), ("id", "worker_template", "intent", "goal_ref"))
    steps = [{"id": r["id"], "agent": r["worker_template"], "intent": r["intent"], "goal": r["goal_ref"]} for r in steps]
    for index, row in enumerate(steps, start=1):
        row["outcome"] = outcomes.get(row["id"]) or outcomes.get(str(index), "")
    return {"at": int(last.get("at") or 0), "steps": steps, "done": len(outcomes)}


def shadow() -> dict:
    totals = {k: int(v) for k, v in swarm.stats.items()}
    gate = swarm.store.gate() if swarm.store is not None else {"observed_days": 0, "clean_days": 0, "window_mismatches": 0,
                                                              "streak": 0, "ready": False}
    return {"totals": totals, "gate": gate, "persistent": swarm.store is not None}


def snapshot() -> dict:
    return {"graph": graph.overview(), "plan": plan(), "consultations": graph.consultations(30), "shadow": shadow()}
