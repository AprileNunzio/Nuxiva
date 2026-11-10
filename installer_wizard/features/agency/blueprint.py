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
class Decision:
    id: str
    title: str
    rationale: str
    status: str = "proposed"

    def spec(self) -> dict:
        return {"id": self.id, "title": self.title, "rationale": self.rationale, "status": self.status}


@dataclass
class QuestionOption:
    id: str
    label: str
    description: str = ""

    def spec(self) -> dict:
        return {"id": self.id, "label": self.label, "description": self.description}


@dataclass
class Question:
    id: str
    prompt: str
    options: list[QuestionOption] = field(default_factory=list)
    selected_option: str | None = None
    answer: str | None = None

    def spec(self) -> dict:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "options": [o.spec() for o in self.options],
        }


@dataclass
class Proof:
    criterion: str
    command: str
    expected_output: str
    actual_output: str | None = None
    verified: bool = False
    artifact_hash: str | None = None

    def spec(self) -> dict:
        return {
            "criterion": self.criterion,
            "command": self.command,
            "expected_output": self.expected_output,
            "actual_output": self.actual_output,
            "verified": self.verified,
            "artifact_hash": self.artifact_hash,
        }


@dataclass
class TaskPlan:
    id: str
    title: str
    role: str
    depends_on: list[str] = field(default_factory=list)
    acceptance: list[str] = field(default_factory=list)
    estimate_seconds: int = 600
    budget_tokens: int | None = None
    budget_seconds: int | None = None
    proofs: list[Proof] = field(default_factory=list)

    def spec(self) -> dict:
        spec_data = {
            "id": self.id,
            "title": self.title,
            "role": self.role,
            "depends_on": self.depends_on,
            "acceptance": self.acceptance,
            "estimate_seconds": self.estimate_seconds,
            "max_attempts": 3,
        }
        if self.budget_tokens is not None:
            spec_data["budget_tokens"] = self.budget_tokens
        if self.budget_seconds is not None:
            spec_data["budget_seconds"] = self.budget_seconds
        return spec_data


@dataclass
class Blueprint:
    title: str
    summary: str
    architecture: str
    roles: list[Role]
    tasks: list[TaskPlan]
    decisions: list[Decision] = field(default_factory=list)
    questions: list[Question] = field(default_factory=list)

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
        budget_tokens = int(item["budget_tokens"]) if isinstance(item.get("budget_tokens"), (int, float)) and item["budget_tokens"] > 0 else None
        budget_seconds = int(item["budget_seconds"]) if isinstance(item.get("budget_seconds"), (int, float)) and item["budget_seconds"] > 0 else None
        tasks.append(TaskPlan(task_id, title, role, [d for d in dict.fromkeys(deps) if d in ids][:16],
                              strings(item.get("acceptance"), CRITERION, 8), _estimate(item.get("estimate_seconds")),
                              budget_tokens=budget_tokens, budget_seconds=budget_seconds))
        ids.add(task_id)
        if len(tasks) >= MAX_TASKS:
            break
    return tasks


def _decisions(raw) -> list[Decision]:
    out = []
    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, dict):
            d_id = slug(item.get("id") or item.get("title"), 40, f"d{len(out)+1}")
            title = clean(item.get("title"), TITLE)
            rationale = clean(item.get("rationale") or item.get("description"), 2000)
            status = clean(item.get("status") or "proposed", 32)
            if title:
                out.append(Decision(d_id, title, rationale, status))
    return out[:32]


def _questions(raw) -> list[Question]:
    out = []
    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, dict):
            q_id = slug(item.get("id") or item.get("prompt"), 40, f"q{len(out)+1}")
            prompt = clean(item.get("prompt") or item.get("question"), 1000)
            options = []
            for opt in item.get("options", []) if isinstance(item.get("options"), list) else []:
                if isinstance(opt, dict):
                    opt_id = slug(opt.get("id") or opt.get("label"), 32, f"opt{len(options)+1}")
                    label = clean(opt.get("label") or opt.get("title"), 200)
                    desc = clean(opt.get("description") or opt.get("desc"), 500)
                    if label:
                        options.append(QuestionOption(opt_id, label, desc))
            if prompt:
                out.append(Question(q_id, prompt, options))
    return out[:16]


def parse(raw, goal: str) -> Blueprint:
    data = raw if isinstance(raw, dict) else {}
    roles = _roles(data.get("roles"))
    if not roles:
        roles = [Role("generalist", "")]
    return Blueprint(clean(data.get("title") or goal, TITLE), clean(data.get("summary"), SUMMARY),
                     clean(data.get("architecture"), ARCHITECTURE), roles,
                     _tasks(data.get("tasks"), {r.id for r in roles}),
                     _decisions(data.get("decisions")),
                     _questions(data.get("questions")))


def extend(blueprint: Blueprint, raw) -> list[TaskPlan]:
    known = {t.id for t in blueprint.tasks}
    room = MAX_TASKS - len(blueprint.tasks)
    if room <= 0:
        return []
    added = _tasks(raw, {r.id for r in blueprint.roles}, len(blueprint.tasks), known)[:room]
    blueprint.tasks.extend(added)
    return added
