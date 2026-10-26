import re
import time
import uuid
from dataclasses import asdict, dataclass, field

from features.experts.model import clean

ID_RE = re.compile(r"^p[0-9a-f]{10}$")
STEP_RE = re.compile(r"^s[0-9]{1,2}$")
PROJECT_STATES = ("planning", "running", "paused", "done", "failed", "cancelled")
STEP_STATES = ("pending", "running", "review", "done", "failed", "waiting")
ACTIVE = ("planning", "running")
MAX_STEPS = 40
MAX_DIRECTIVES = 10
MAX_LOG = 60
MAX_PROJECTS = 50
KINDS = ("general", "3d")
THREE_D = re.compile(r"\b3\s*d\b|\btridimension\w*|\btre\s+dimensioni\b|\bthree[- ]dimensional\b|\bstampa\s+3\s*d\b|\b3d\s+print\w*", re.I)
MODEL_STEP = {"it": "Modella l'oggetto in 3D nello studio", "en": "Model the object in 3D in the studio",
              "es": "Modela el objeto en 3D en el estudio", "fr": "Modéliser l'objet en 3D dans le studio"}
LIMITS = {"title": 80, "goal": 1500, "text": 300, "result": 2000, "error": 300, "acceptance": 300, "feedback": 600, "directive": 400}


class ProjectError(ValueError):
    pass


@dataclass
class Step:
    id: str
    text: str
    status: str = "pending"
    expert_id: str = ""
    expert_role: str = ""
    result: str = ""
    error: str = ""
    started: float = 0.0
    finished: float = 0.0
    action: str = ""
    depends: list[str] = field(default_factory=list)
    acceptance: str = ""
    round: int = 0
    feedback: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Project:
    id: str
    title: str
    goal: str
    lang: str = "it"
    status: str = "planning"
    steps: list[Step] = field(default_factory=list)
    error: str = ""
    kind: str = "general"
    model_id: str = ""
    created: float = field(default_factory=time.time)
    updated: float = field(default_factory=time.time)
    workspace: str = ""
    directives: list[str] = field(default_factory=list)
    log: list[dict] = field(default_factory=list)
    final_rounds: int = 0

    @property
    def progress(self) -> int:
        if not self.steps:
            return 0
        return round(100 * sum(1 for s in self.steps if s.status == "done") / len(self.steps))

    def to_dict(self) -> dict:
        return {**asdict(self), "progress": self.progress}


def note(project: Project, kind: str, text: str) -> None:
    project.log.append({"at": time.time(), "kind": kind[:20], "text": clean(text, LIMITS["text"])})
    del project.log[:-MAX_LOG]


def new_id() -> str:
    return f"p{uuid.uuid4().hex[:10]}"


def title_of(goal: str) -> str:
    first = re.split(r"[.!?\n]", goal, maxsplit=1)[0]
    return clean(first, LIMITS["title"]) or clean(goal, LIMITS["title"])


def create(goal: str, lang: str, title: str = "") -> Project:
    goal = clean(goal, LIMITS["goal"])
    if len(goal) < 8:
        raise ProjectError("Descrivi l'obiettivo del progetto con qualche parola in più")
    return Project(new_id(), clean(title, LIMITS["title"]) or title_of(goal), goal, lang if lang in ("it", "en", "es", "fr") else "it",
                   kind="3d" if THREE_D.search(goal) else "general")


def with_modelling(steps: list[Step], lang: str) -> list[Step]:
    ordered = [Step("s1", MODEL_STEP.get(lang, MODEL_STEP["it"]), action="model3d")] + steps[:MAX_STEPS - 1]
    renamed = {step.id: f"s{i + 1}" for i, step in enumerate(ordered[1:], start=1)}
    for step in ordered[1:]:
        step.depends = [renamed[d] for d in step.depends if d in renamed]
    for i, step in enumerate(ordered):
        step.id = f"s{i + 1}"
    return ordered


def _depends(raw, index: int) -> list[str]:
    found = []
    for item in raw if isinstance(raw, list) else []:
        text = str(item).lower().lstrip("s")
        if text.isdigit() and 1 <= int(text) <= index:
            found.append(f"s{int(text)}")
    return list(dict.fromkeys(found))


def steps_from(rows) -> list[Step]:
    if not isinstance(rows, list):
        raise ProjectError("Piano non valido")
    steps: list[Step] = []
    for row in rows:
        data = row if isinstance(row, dict) else {"text": row}
        text = clean(data.get("text") or data.get("step") or data.get("title"), LIMITS["text"])
        if len(text) < 3 or text in [s.text for s in steps] or len(steps) >= MAX_STEPS:
            continue
        steps.append(Step(f"s{len(steps) + 1}", text, acceptance=clean(data.get("acceptance"), LIMITS["acceptance"]),
                          depends=_depends(data.get("depends"), len(steps))))
    if not steps:
        raise ProjectError("Piano vuoto")
    return steps


def restore(row: dict) -> Project:
    if not isinstance(row, dict) or not ID_RE.fullmatch(str(row.get("id") or "")):
        raise ProjectError("Progetto non valido")
    steps = []
    for item in row.get("steps") or []:
        if not isinstance(item, dict) or not STEP_RE.fullmatch(str(item.get("id") or "")):
            continue
        status = item.get("status") if item.get("status") in STEP_STATES else "pending"
        steps.append(Step(item["id"], clean(item.get("text"), LIMITS["text"]), status, clean(item.get("expert_id"), 40),
                          clean(item.get("expert_role"), 80), clean(item.get("result"), LIMITS["result"]),
                          clean(item.get("error"), LIMITS["error"]), float(item.get("started") or 0), float(item.get("finished") or 0),
                          "model3d" if item.get("action") == "model3d" else "", _depends(item.get("depends"), 99),
                          clean(item.get("acceptance"), LIMITS["acceptance"]), int(item.get("round") or 0),
                          clean(item.get("feedback"), LIMITS["feedback"])))
    status = row.get("status") if row.get("status") in PROJECT_STATES else "paused"
    return Project(row["id"], clean(row.get("title"), LIMITS["title"]), clean(row.get("goal"), LIMITS["goal"]),
                   row.get("lang") if row.get("lang") in ("it", "en", "es", "fr") else "it", status, steps,
                   clean(row.get("error"), LIMITS["error"]), row.get("kind") if row.get("kind") in KINDS else "general",
                   clean(row.get("model_id"), 80), float(row.get("created") or time.time()), float(row.get("updated") or time.time()),
                   clean(row.get("workspace"), 60), [clean(d, LIMITS["directive"]) for d in (row.get("directives") or [])][:MAX_DIRECTIVES],
                   [{"at": float(e.get("at") or 0), "kind": clean(e.get("kind"), 20), "text": clean(e.get("text"), LIMITS["text"])}
                    for e in (row.get("log") or []) if isinstance(e, dict)][-MAX_LOG:], int(row.get("final_rounds") or 0))
