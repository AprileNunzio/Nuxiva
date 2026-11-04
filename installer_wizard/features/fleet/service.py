from pathlib import Path

from config import STATE_DIR
from state import store as audit

from features.fleet import catalog
from features.fleet.model import FleetError, build_spec, require_id, require_ref, slug
from features.fleet.store import Filter, FleetStore

ROOT = STATE_DIR / "fleet"


class FleetService:
    def __init__(self, root: Path) -> None:
        self.store = FleetStore(root)

    def _validate_refs(self, tools: list[str], widgets: list[str]) -> None:
        for name in tools:
            if not catalog.has_tool(require_ref(name)):
                raise FleetError("unknown_tool", 422)
        for widget_id in widgets:
            if not catalog.has_widget(require_ref(widget_id)):
                raise FleetError("unknown_widget", 422)

    def _refs(self, raw: object, key: str) -> list[str]:
        values = raw.get(key, []) if isinstance(raw, dict) else []
        if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
            raise FleetError("invalid_body")
        return values

    def create(self, raw: object, origin: str, actor: str) -> dict:
        spec = build_spec(raw, origin)
        tools, widgets = self._refs(raw, "tools"), self._refs(raw, "widgets")
        self._validate_refs(tools, widgets)
        self.store.create(spec)
        if tools:
            self.store.link(spec.id, "tool", tools)
        if widgets:
            self.store.link(spec.id, "widget", widgets)
        audit.event("INFO", f"Agente {spec.id} creato da {actor}", "fleet")
        return self.store.get(spec.id)

    def unique_id(self, name: str) -> str:
        base = require_id(slug(name))
        candidate, number = base, 1
        while self.store.exists(candidate):
            number += 1
            candidate = f"{base[:56]}-{number}"
        return candidate

    def unique_widget_id(self, name: str) -> str:
        base = require_ref(slug(name))
        candidate, number = base, 1
        while catalog.has_widget(candidate):
            number += 1
            candidate = f"{base[:56]}-{number}"
        return candidate

    def update(self, agent_id: str, changes: dict, actor: str) -> dict:
        record = self.store.update(agent_id, changes)
        audit.event("INFO", f"Agente {agent_id} aggiornato da {actor}", "fleet")
        return record

    def delete(self, agent_id: str, actor: str) -> None:
        self.store.delete(agent_id)
        audit.event("INFO", f"Agente {agent_id} eliminato da {actor}", "fleet")

    def link(self, agent_id: str, kind: str, refs: list[str], actor: str) -> dict:
        if kind == "tool":
            self._validate_refs(refs, [])
        elif kind == "widget":
            self._validate_refs([], refs)
        self.store.link(agent_id, kind, refs)
        audit.event("INFO", f"Agente {agent_id}: {kind} collegati da {actor}", "fleet")
        return self.store.get(agent_id)

    def unlink(self, agent_id: str, kind: str, ref: str, actor: str) -> dict:
        self.store.unlink(agent_id, kind, ref)
        audit.event("INFO", f"Agente {agent_id}: {kind} {ref} scollegato da {actor}", "fleet")
        return self.store.get(agent_id)

    def detail(self, agent_id: str) -> dict:
        record = self.store.get(agent_id)
        record["missing_tools"] = [name for name in record["tools"] if not catalog.has_tool(name)]
        record["missing_widgets"] = [name for name in record["widgets"] if not catalog.has_widget(name)]
        return record

    def bulk_state(self, flt: Filter, state: str, actor: str) -> dict:
        outcome = self.store.change_state(flt, state)
        audit.event("INFO", f"Agenti: {outcome['changed']} portati a {state} da {actor}", "fleet")
        return outcome


fleet = FleetService(ROOT)
