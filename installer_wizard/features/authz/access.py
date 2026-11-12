import json
import re
from dataclasses import dataclass
from pathlib import Path

COLUMNS = ("owner", "family", "staff", "child", "guest", "anonymous")
CELLS = ("allow", "room", "own", "confirm", "strong", "deny")
STRENGTHS = ("none", "weak", "single", "strong")
DEFAULT_FILE = Path(__file__).with_name("matrix") / "default.json"
FALLBACK = "risk.critical"
MAX_MATRIX = 256 * 1024
MAX_RULES = 1024
MAX_CAPABILITIES = 64
SEGMENT = re.compile(r"^[a-z_]{1,32}$")
OUTSIDER_DENY = ("home.lock.unlock", "home.alarm.disarm", "home.gate.open", "home.valve.set", "home.camera.",
                 "home.automation.", "home.private.", "home.system.", "comm.", "commerce.", "system.", "sentinel.",
                 "people.", "memory.", "files.", "risk.critical")
STRONG_FOR_ALL = ("home.lock.unlock", "home.alarm.disarm", "home.valve.set", "commerce.", "system.admin.", "sentinel.")
ROLE_ALIASES = {"friend": "staff"}


class MatrixError(ValueError):

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Verdict:
    kind: str
    detail: str = ""


def valid_capability(raw: str) -> bool:
    parts = raw.split(".") if isinstance(raw, str) else []
    return 2 <= len(parts) <= 3 and all(SEGMENT.match(p) for p in parts)


def _valid_pattern(raw: str) -> bool:
    if raw.endswith(".*"):
        prefix = raw[:-2]
        return "*" not in prefix and valid_capability(prefix + ".x")
    return valid_capability(raw)


def _covered(pattern: str, listing: tuple[str, ...]) -> bool:
    bare = pattern.rstrip("*")
    return any((bare.startswith(p) or p.startswith(bare)) if p.endswith(".") else (bare == p or p.startswith(bare))
               for p in listing)


def harden(pattern: str, cells: list[str]) -> list[str]:
    floor = ["allow"] * len(COLUMNS)
    if _covered(pattern, STRONG_FOR_ALL):
        floor = ["strong"] * len(COLUMNS)
    if _covered(pattern, OUTSIDER_DENY):
        floor[4] = floor[5] = "deny"
    return [CELLS[max(CELLS.index(c), CELLS.index(f))] for c, f in zip(cells, floor)]


def candidates(capability: str) -> list[str]:
    parts = capability.split(".")
    return [capability] + [".".join(parts[:n]) + ".*" for n in range(len(parts) - 1, 0, -1)]


def role_column(role: str) -> str:
    role = ROLE_ALIASES.get(role, role)
    return role if role in COLUMNS or role == "system" else "anonymous"


class Matrix:

    def __init__(self, rules: dict[str, list[str]]) -> None:
        self.rules = rules

    @classmethod
    def parse(cls, raw: str) -> "Matrix":
        if len(raw) > MAX_MATRIX:
            raise MatrixError("access.error.too_large")
        try:
            data = json.loads(raw)
        except ValueError as exc:
            raise MatrixError("access.error.schema") from exc
        if not isinstance(data, dict) or set(data) != {"version", "rules"} or not isinstance(data["rules"], dict):
            raise MatrixError("access.error.schema")
        if data["version"] != 1:
            raise MatrixError("access.error.version")
        if len(data["rules"]) > MAX_RULES or FALLBACK not in data["rules"]:
            raise MatrixError("access.error.schema")
        rules = {}
        for key, cells in data["rules"].items():
            if not _valid_pattern(key):
                raise MatrixError("access.error.capability")
            if not isinstance(cells, list) or len(cells) != len(COLUMNS):
                raise MatrixError("access.error.schema")
            if any(c not in CELLS for c in cells):
                raise MatrixError("access.error.cell")
            rules[key] = harden(key, list(cells))
        return cls(rules)

    @classmethod
    def builtin(cls) -> "Matrix":
        return cls.parse(DEFAULT_FILE.read_text(encoding="utf-8"))

    def cell(self, capability: str, role: str) -> str:
        column = role_column(role)
        if column == "system":
            return "allow"
        row = next((self.rules[k] for k in candidates(capability) if k in self.rules), self.rules[FALLBACK])
        return row[COLUMNS.index(column)]

    def export(self) -> dict[str, list[str]]:
        return {k: list(v) for k, v in sorted(self.rules.items())}


RANK = {"allow": 0, "confirm": 1, "proof": 2, "deny": 3}


def _single(cell: str, column: str, strength: str, local: bool | None, own: bool) -> Verdict:
    level = STRENGTHS.index(strength) if strength in STRENGTHS else 0
    if cell == "allow":
        return Verdict("allow")
    if cell == "room":
        return Verdict("deny", "room") if local is False else Verdict("allow")
    if cell == "own":
        return Verdict("allow") if own else Verdict("deny", "owner_data")
    if cell == "confirm":
        return Verdict("confirm") if level >= 2 else Verdict("proof", "single")
    if cell == "strong":
        return Verdict("allow") if level >= 3 else Verdict("proof", "strong")
    return Verdict("deny", "guest" if column in ("guest", "anonymous") else "role")


class PythonEngine:

    def __init__(self, raw: str | None = None) -> None:
        self.matrix = Matrix.parse(raw) if raw is not None else Matrix.builtin()

    def decide(self, capabilities: list[str], role: str, level: str, local: bool | None = None,
               own: bool = False) -> tuple[str, str]:
        if len(capabilities) > MAX_CAPABILITIES:
            raise MatrixError("access.error.too_many")
        if any(not valid_capability(c) for c in capabilities):
            raise MatrixError("access.error.capability")
        column = role_column(role)
        if not capabilities:
            verdict = _single("deny", column, level, local, own)
        else:
            verdict = Verdict("deny", "role")
            for index, capability in enumerate(capabilities):
                step = _single(self.matrix.cell(capability, role), column, level, local, own)
                if index == 0 or RANK[step.kind] >= RANK[verdict.kind]:
                    verdict = step
        return verdict.kind, verdict.detail

    def export(self) -> str:
        return json.dumps(self.matrix.export())
