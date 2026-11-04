from dataclasses import asdict, dataclass, field

from features.agency.text import clean, slug, strings

MAX_TASKS = 60
MAX_ROLES = 16
TITLE = 120
SUMMARY = 1200
ARCHITECTURE = 4000
TASK_TITLE = 280
CRITERION = 400
ESTIMATE_MAX = 6 * 3600


@dataclass
class Role:
    id: str
    mission: str


@dataclass
class TaskPlan:
    id: str
    title: str
    role: str
    depends_on: list[str] = field(default_factory=list)
    acceptance: list[str] = field(default_factory=list)
    estimate_seconds: int = 600

    def spec(self) -> dict:
        return {"id": self.id, "title": self.title, "role": self.role, "depends_on": self.depends_on,
                "acceptance": self.acceptance, "estimate_seconds": self.estimate_seconds, "max_attempts": 3}


@dataclass
class Blueprint:
    title: str
    summary: str
    architecture: str
    roles: list[Role]
    tasks: list[TaskPlan]

    def to_dict(self) -> dict:
        return asdict(self)

    def role_of(self, role_id: str) -> Role | None:
        return next((r for r in self.roles if r.id == role_id), None)


def _estimate(value) -> int:
    try:
        seconds = int(float(value))
    except (TypeError, ValueError):
        return 600
    return max(60, min(seconds, ESTIMATE_MAX))


def _roles(raw) -> list[Role]:
    roles, seen = [], set()
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        role_id = slug(item.get("id") or item.get("name"), 32, "")
        if not role_id or role_id in seen:
            continue
        seen.add(role_id)
        roles.append(Role(role_id, clean(item.get("mission") or item.get("description"), 400)))
    return roles[:MAX_ROLES]


def _tasks(raw, roles: set[str], start: int = 0, known: set[str] | None = None) -> list[TaskPlan]:
    tasks, ids = [], set(known or ())
    for index, item in enumerate(raw if isinstance(raw, list) else [], start=start + 1):
        if not isinstance(item, dict):
            continue
        title = clean(item.get("title"), TASK_TITLE)
        if not title:
            continue
        task_id = slug(item.get("id") or title, 40, f"t{index}")
        while task_id in ids:
            task_id = f"{task_id[:34]}-{index}"
        role = slug(item.get("role"), 32, "")
        role = role if role in roles else next(iter(sorted(roles)), "generalist")
        deps = [slug(d, 40, "") for d in item.get("depends_on", []) if isinstance(d, str)] if isinstance(item.get("depends_on"), list) else []
        tasks.append(TaskPlan(task_id, title, role, [d for d in dict.fromkeys(deps) if d in ids][:16],
                              strings(item.get("acceptance"), CRITERION, 8), _estimate(item.get("estimate_seconds"))))
        ids.add(task_id)
        if len(tasks) >= MAX_TASKS:
            break
    return tasks


def parse(raw, goal: str) -> Blueprint:
    data = raw if isinstance(raw, dict) else {}
    roles = _roles(data.get("roles"))
    if not roles:
        roles = [Role("generalist", "")]
    return Blueprint(clean(data.get("title") or goal, TITLE), clean(data.get("summary"), SUMMARY),
                     clean(data.get("architecture"), ARCHITECTURE), roles,
                     _tasks(data.get("tasks"), {r.id for r in roles}))


def extend(blueprint: Blueprint, raw) -> list[TaskPlan]:
    known = {t.id for t in blueprint.tasks}
    room = MAX_TASKS - len(blueprint.tasks)
    if room <= 0:
        return []
    added = _tasks(raw, {r.id for r in blueprint.roles}, len(blueprint.tasks), known)[:room]
    blueprint.tasks.extend(added)
    return added
