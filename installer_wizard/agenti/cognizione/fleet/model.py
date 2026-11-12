import re
import unicodedata
from dataclasses import dataclass

ID = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")
REF = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")
STATES = ("active", "paused", "archived")
KINDS = ("assistant", "sensor", "home", "knowledge", "comms", "media", "system", "custom")
CATEGORIES = ("assistente", "percezione", "casa", "conoscenza", "comunicazione", "intrattenimento", "sistema", "altro")
ORIGINS = ("user", "nuxiva")
LINK_KINDS = ("tool", "widget")
MAX_LIMIT = 200
DEFAULT_LIMIT = 50
BULK_MAX = 1000
NAME_MAX = 80
DESCRIPTION_MAX = 400
INSTRUCTIONS_MAX = 4000
LINKS_MAX = 200
PRIORITY_MAX = 200


class FleetError(ValueError):
    def __init__(self, code: str, status: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


def clean_text(value: object, limit: int, multiline: bool = False) -> str:
    if not isinstance(value, str):
        return ""
    text = unicodedata.normalize("NFKC", value)
    allowed = {"\n"} if multiline else set()
    kept = "".join(ch for ch in text if ch in allowed or (unicodedata.category(ch)[0] != "C" and ch not in "<>"))
    return kept.strip()[:limit]


def require_id(value: object) -> str:
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise FleetError("invalid_id")
    return value


def require_ref(value: object) -> str:
    if not isinstance(value, str) or not REF.fullmatch(value):
        raise FleetError("invalid_ref")
    return value


def require_choice(value: object, options: tuple[str, ...], code: str) -> str:
    if not isinstance(value, str) or value not in options:
        raise FleetError(code)
    return value


def require_priority(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= PRIORITY_MAX:
        raise FleetError("invalid_priority")
    return value


def slug(text: str) -> str:
    base = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    if not base or not base[0].isalpha():
        base = f"agent-{base}".strip("-")
    return base[:60].rstrip("-")


@dataclass(frozen=True, slots=True)
class AgentSpec:
    id: str
    name: str
    kind: str
    category: str
    state: str
    priority: int
    origin: str
    description: str
    instructions: str


def build_spec(raw: object, origin: str) -> AgentSpec:
    if not isinstance(raw, dict):
        raise FleetError("invalid_body")
    name = clean_text(raw.get("name"), NAME_MAX)
    if not name:
        raise FleetError("invalid_name")
    identifier = raw.get("id") if raw.get("id") is not None else slug(name)
    return AgentSpec(
        id=require_id(identifier),
        name=name,
        kind=require_choice(raw.get("kind", "custom"), KINDS, "invalid_kind"),
        category=require_choice(raw.get("category", "altro"), CATEGORIES, "invalid_category"),
        state=require_choice(raw.get("state", "active"), STATES, "invalid_state"),
        priority=require_priority(raw.get("priority", 50)),
        origin=require_choice(origin, ORIGINS, "invalid_origin"),
        description=clean_text(raw.get("description", ""), DESCRIPTION_MAX),
        instructions=clean_text(raw.get("instructions", ""), INSTRUCTIONS_MAX, multiline=True),
    )
