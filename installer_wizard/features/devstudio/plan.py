import json
import os
import re
import time
from dataclasses import dataclass, field

from config import STATE_DIR

from features.devstudio import workspace
from features.devstudio.workspace import DevError

PLAN_DIR = STATE_DIR / "devstudio"
MAX_PLAN_FILES = 80
GOAL_LIMIT = 4000
PURPOSE_LIMIT = 300
STATUSES = ("pending", "done", "failed")


@dataclass
class Item:
    path: str
    purpose: str
    status: str = "pending"
    note: str = ""


@dataclass
class Plan:
    project: str
    goal: str
    stack: str
    items: list[Item] = field(default_factory=list)
    updated: float = 0.0

    def pending(self) -> list[Item]:
        return [i for i in self.items if i.status == "pending"]

    def counts(self) -> dict[str, int]:
        return {s: sum(1 for i in self.items if i.status == s) for s in STATUSES}


def _file(project: str):
    return PLAN_DIR / f"{workspace.slug(project)}.json"


def _item(raw: dict, folder) -> Item:
    if not isinstance(raw, dict):
        raise DevError("elemento del piano non valido")
    relative = str(raw.get("path") or "").replace("\\", "/").strip("/")
    workspace.safe_path(folder, relative)
    purpose = re.sub(r"\s+", " ", str(raw.get("purpose") or "")).strip()[:PURPOSE_LIMIT]
    status = raw.get("status") if raw.get("status") in STATUSES else "pending"
    return Item(relative, purpose, status, str(raw.get("note") or "")[:200])


def build(project: str, goal: str, stack: str, files: list) -> Plan:
    folder = workspace.project_dir(project)
    if not isinstance(files, list) or not files:
        raise DevError("il piano non contiene file")
    seen: dict[str, Item] = {}
    for raw in files[:MAX_PLAN_FILES]:
        item = _item(raw, folder)
        seen.setdefault(item.path, item)
    return Plan(workspace.slug(project), str(goal)[:GOAL_LIMIT], str(stack)[:200], list(seen.values()), time.time())


def save(plan: Plan) -> None:
    PLAN_DIR.mkdir(parents=True, exist_ok=True)
    target = _file(plan.project)
    temp = target.with_suffix(".tmp")
    plan.updated = time.time()
    temp.write_text(json.dumps({"project": plan.project, "goal": plan.goal, "stack": plan.stack, "updated": plan.updated,
                                "items": [vars(i) for i in plan.items]}, ensure_ascii=False), encoding="utf-8")
    os.chmod(temp, 0o600)
    temp.replace(target)


def load(project: str) -> Plan:
    target = _file(project)
    if not target.is_file():
        raise DevError(f"nessun piano per «{workspace.slug(project)}»: crealo con dev_plan")
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DevError(f"piano illeggibile: {type(exc).__name__}") from exc
    folder = workspace.project_dir(project)
    return Plan(str(raw["project"]), str(raw.get("goal", "")), str(raw.get("stack", "")),
                [_item(i, folder) for i in raw.get("items", [])], float(raw.get("updated", 0)))
