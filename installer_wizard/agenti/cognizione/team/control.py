import json
import logging
import os
import re
import threading

from config import STATE_DIR

log = logging.getLogger("nuxiva.team")
FILE = STATE_DIR / "team_control.json"
AGENT_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{1,40}$")
TOOL_ID = re.compile(r"^[a-z][a-z0-9_]{1,60}$")
WIDGET_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{1,40}$")
SLUG = re.compile(r"^[a-z0-9_][a-z0-9_-]{0,63}$")
MAX_INSTRUCTIONS = 1500
MIN_PRIORITY, MAX_PRIORITY = 0, 200
MAX_PEOPLE = 32


def _empty() -> dict:
    return {"agents": {}, "tools": {}, "widgets": {}}


def _text(value, limit: int) -> str:
    return re.sub(r"[\x00-\x08\x0b-\x1f<>]", "", str(value or "")).strip()[:limit]


class TeamControl:
    def __init__(self, path=FILE) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._data: dict | None = None

    def _all(self) -> dict:
        if self._data is None:
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                raw = {}
            except (OSError, ValueError) as exc:
                log.warning("Controllo agenti illeggibile, riparto dai valori predefiniti: %s", exc)
                raw = {}
            data = _empty()
            for key in data:
                if isinstance(raw.get(key), dict):
                    data[key] = raw[key]
            self._data = data
        return self._data

    def _save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._all(), ensure_ascii=False, indent=1), encoding="utf-8")
        os.chmod(tmp, 0o600)
        os.replace(tmp, self.path)

    def agent(self, agent_id: str) -> dict:
        return dict(self._all()["agents"].get(agent_id) or {})

    def tool(self, name: str) -> dict:
        return dict(self._all()["tools"].get(name) or {})

    def widget(self, wid: str) -> dict:
        return dict(self._all()["widgets"].get(wid) or {})

    def priority(self, agent_id: str) -> int | None:
        value = self.agent(agent_id).get("priority")
        return value if isinstance(value, int) else None

    def instructions(self, agent_id: str) -> str:
        return str(self.agent(agent_id).get("instructions") or "")

    def tool_owner(self, name: str) -> str | None:
        owner = self.tool(name).get("agent")
        return owner if isinstance(owner, str) and AGENT_ID.match(owner) else None

    def tool_enabled(self, name: str) -> bool:
        return self.tool(name).get("enabled", True) is not False

    def tool_forced_confirm(self, name: str) -> bool:
        return self.tool(name).get("always_confirm") is True

    def widget_owner(self, wid: str) -> str | None:
        owner = self.widget(wid).get("agent")
        return owner if isinstance(owner, str) and AGENT_ID.match(owner) else None

    def widget_people(self, wid: str) -> list[str]:
        people = self.widget(wid).get("people")
        return [p for p in people if isinstance(p, str) and SLUG.match(p)] if isinstance(people, list) else []

    def set_agent(self, agent_id: str, changes: dict) -> dict:
        if not AGENT_ID.match(agent_id) or not isinstance(changes, dict):
            raise ValueError("Agente non valido")
        with self._lock:
            row = self._all()["agents"].setdefault(agent_id, {})
            if "priority" in changes:
                value = changes["priority"]
                if value is None:
                    row.pop("priority", None)
                elif isinstance(value, int) and not isinstance(value, bool) and MIN_PRIORITY <= value <= MAX_PRIORITY:
                    row["priority"] = value
                else:
                    raise ValueError("Priorità non valida")
            if "instructions" in changes:
                text = _text(changes["instructions"], MAX_INSTRUCTIONS)
                if text:
                    row["instructions"] = text
                else:
                    row.pop("instructions", None)
            if not row:
                self._all()["agents"].pop(agent_id, None)
            self._save()
            return dict(row)

    def set_tool(self, name: str, changes: dict, known_agents: set[str]) -> dict:
        if not TOOL_ID.match(name) or not isinstance(changes, dict):
            raise ValueError("Strumento non valido")
        with self._lock:
            row = self._all()["tools"].setdefault(name, {})
            if "agent" in changes:
                owner = changes["agent"]
                if owner in (None, ""):
                    row.pop("agent", None)
                elif isinstance(owner, str) and owner in known_agents:
                    row["agent"] = owner
                else:
                    raise ValueError("Agente non valido")
            if "enabled" in changes:
                if not isinstance(changes["enabled"], bool):
                    raise ValueError("Valore non valido")
                if changes["enabled"]:
                    row.pop("enabled", None)
                else:
                    row["enabled"] = False
            if "always_confirm" in changes:
                if not isinstance(changes["always_confirm"], bool):
                    raise ValueError("Valore non valido")
                if changes["always_confirm"]:
                    row["always_confirm"] = True
                else:
                    row.pop("always_confirm", None)
            if not row:
                self._all()["tools"].pop(name, None)
            self._save()
            return dict(row)

    def set_widget(self, wid: str, changes: dict, known_agents: set[str], known_people: set[str]) -> dict:
        if not WIDGET_ID.match(wid) or not isinstance(changes, dict):
            raise ValueError("Widget non valido")
        with self._lock:
            row = self._all()["widgets"].setdefault(wid, {})
            if "agent" in changes:
                owner = changes["agent"]
                if owner in (None, ""):
                    row.pop("agent", None)
                elif isinstance(owner, str) and owner in known_agents:
                    row["agent"] = owner
                else:
                    raise ValueError("Agente non valido")
            if "people" in changes:
                people = changes["people"]
                if not isinstance(people, list) or len(people) > MAX_PEOPLE or not all(isinstance(p, str) and p in known_people for p in people):
                    raise ValueError("Persone non valide")
                if people:
                    row["people"] = sorted(set(people))
                else:
                    row.pop("people", None)
            if not row:
                self._all()["widgets"].pop(wid, None)
            self._save()
            return dict(row)

    def forget_agent(self, agent_id: str) -> None:
        with self._lock:
            data = self._all()
            data["agents"].pop(agent_id, None)
            for bucket in ("tools", "widgets"):
                for row in data[bucket].values():
                    if row.get("agent") == agent_id:
                        row.pop("agent", None)
            self._save()


control = TeamControl()
