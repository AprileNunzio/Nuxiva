import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from config import STATE_DIR
from sealed import SealedFile

from features.agency.forge.guard import ForgeRejected, check, name

PREFIX = "x_"
MAX_ACTIVE = 100
RETIRE_FAILS = 5
ACTIVE = "active"
RETIRED = "retired"


@dataclass
class ForgedTool:
    name: str
    description: str
    args: dict
    code: str
    tests: list
    origin: dict
    status: str = ACTIVE
    created_at: float = field(default_factory=time.time)
    uses: int = 0
    fails: int = 0
    last_error: str = ""
    retired_reason: str = ""

    @property
    def call_name(self) -> str:
        return PREFIX + self.name

    def public(self, with_code: bool = False) -> dict:
        data = asdict(self)
        if not with_code:
            data.pop("code")
        data["call_name"] = self.call_name
        return data


class Registry:
    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or STATE_DIR / "agency"

    def _file(self) -> SealedFile:
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.directory, 0o700)
        return SealedFile(self.directory / "forge.sealed", self.directory / "memory.key")

    def _load(self) -> dict[str, ForgedTool]:
        raw = self._file().load().get("tools", {})
        return {key: ForgedTool(**value) for key, value in raw.items() if isinstance(value, dict)}

    def _save(self, tools: dict[str, ForgedTool]) -> None:
        self._file().save({"tools": {key: asdict(tool) for key, tool in tools.items()}})

    def all(self) -> list[ForgedTool]:
        return sorted(self._load().values(), key=lambda t: t.created_at)

    def active(self) -> list[ForgedTool]:
        return [t for t in self.all() if t.status == ACTIVE]

    def get(self, tool_name: str) -> ForgedTool | None:
        return self._load().get(tool_name)

    def by_call_name(self, call_name: str) -> ForgedTool | None:
        if not isinstance(call_name, str) or not call_name.startswith(PREFIX):
            return None
        tool = self.get(call_name.removeprefix(PREFIX))
        return tool if tool and tool.status == ACTIVE else None

    def add(self, tool: ForgedTool) -> ForgedTool:
        name(tool.name)
        check(tool.code)
        tools = self._load()
        if tool.name in tools:
            raise ForgeRejected(f"a tool named {tool.name} already exists")
        if sum(t.status == ACTIVE for t in tools.values()) >= MAX_ACTIVE:
            raise ForgeRejected("too many active tools, retire some first")
        tools[tool.name] = tool
        self._save(tools)
        return tool

    def record(self, tool_name: str, ok: bool, error: str = "") -> ForgedTool | None:
        tools = self._load()
        tool = tools.get(tool_name)
        if tool is None:
            return None
        if ok:
            tool.uses += 1
        else:
            tool.fails += 1
            tool.last_error = error[:300]
            if tool.fails >= RETIRE_FAILS and tool.fails > tool.uses:
                tool.status, tool.retired_reason = RETIRED, "unreliable"
        self._save(tools)
        return tool

    def set_status(self, tool_name: str, status: str, reason: str = "") -> ForgedTool:
        tools = self._load()
        tool = tools.get(tool_name)
        if tool is None or status not in (ACTIVE, RETIRED):
            raise KeyError(tool_name)
        if status == ACTIVE and tool.status != ACTIVE and sum(t.status == ACTIVE for t in tools.values()) >= MAX_ACTIVE:
            raise ForgeRejected("too many active tools, retire some first")
        tool.status, tool.retired_reason = status, (reason if status == RETIRED else "")
        if status == ACTIVE:
            tool.fails = 0
        self._save(tools)
        return tool

    def delete(self, tool_name: str) -> None:
        tools = self._load()
        if tools.pop(tool_name, None) is None:
            raise KeyError(tool_name)
        self._save(tools)


registry = Registry()
