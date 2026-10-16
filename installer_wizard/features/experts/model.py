import re
import time
import unicodedata
from dataclasses import asdict, dataclass, field

ID_RE = re.compile(r"^[a-z][a-z0-9_-]{2,40}$")
TOOL_RE = re.compile(r"^[a-z][a-z0-9_]{1,60}$")
COLOR_RE = re.compile(r"^#[0-9a-f]{6}$")
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f<>]")
LIVE_KINDS = ("activity", "debian", "football")
MAX_KNOWLEDGE = 16
MAX_TOOLS = 24
LIMITS = {"name": 40, "role": 80, "specialty": 240, "instructions": 1200, "icon": 8}


class ExpertError(ValueError):
    pass


def clean(value, limit: int) -> str:
    text = unicodedata.normalize("NFC", str(value or ""))
    text = CONTROL.sub("", text)
    return re.sub(r"\s+", " ", text).strip()[:limit]


def slug(name: str) -> str:
    flat = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    base = re.sub(r"[^a-z0-9]+", "-", flat).strip("-")[:30]
    return base if len(base) >= 3 and base[0].isalpha() else f"esperto-{base or 'nuovo'}"[:40]


@dataclass
class Expert:
    id: str
    name: str
    role: str
    specialty: str
    icon: str = "🧑‍💼"
    color: str = "#29e0ff"
    knowledge: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    instructions: str = ""
    template: str = ""
    live: str = "activity"
    enabled: bool = True
    created: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


def build(raw: dict, known_tools: set[str]) -> Expert:
    if not isinstance(raw, dict):
        raise ExpertError("Dati dell'esperto non validi")
    expert_id = str(raw.get("id") or "")
    if not ID_RE.fullmatch(expert_id):
        raise ExpertError("Identificativo dell'esperto non valido")
    name = clean(raw.get("name"), LIMITS["name"])
    role = clean(raw.get("role"), LIMITS["role"])
    specialty = clean(raw.get("specialty"), LIMITS["specialty"])
    if len(name) < 2 or len(role) < 3 or len(specialty) < 3:
        raise ExpertError("Nome, ruolo e specialità sono obbligatori")
    knowledge = raw.get("knowledge") or []
    if not isinstance(knowledge, list):
        raise ExpertError("Le conoscenze devono essere un elenco")
    knowledge = [k for k in (clean(x, 200) for x in knowledge[:MAX_KNOWLEDGE]) if k]
    tools = raw.get("tools") or []
    if not isinstance(tools, list):
        raise ExpertError("Gli strumenti devono essere un elenco")
    tools = list(dict.fromkeys(str(t) for t in tools[:MAX_TOOLS]))
    unknown = [t for t in tools if not TOOL_RE.fullmatch(t) or t not in known_tools]
    if unknown:
        raise ExpertError(f"Strumenti sconosciuti: {', '.join(unknown[:5])}")
    color = str(raw.get("color") or "#29e0ff").lower()
    live = str(raw.get("live") or "activity")
    return Expert(
        id=expert_id, name=name, role=role, specialty=specialty,
        icon=clean(raw.get("icon"), LIMITS["icon"]) or "🧑‍💼",
        color=color if COLOR_RE.fullmatch(color) else "#29e0ff",
        knowledge=knowledge, tools=tools,
        instructions=clean(raw.get("instructions"), LIMITS["instructions"]),
        template=str(raw.get("template") or "")[:20],
        live=live if live in LIVE_KINDS else "activity",
        enabled=raw.get("enabled", True) is not False,
        created=float(raw.get("created") or time.time()),
    )
