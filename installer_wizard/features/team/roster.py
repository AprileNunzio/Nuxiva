from feature_registry import registry as features

from features.agent import registry as tools
from features.team import priority
from features.team.board import board
from features.team.control import control

SHORT = 110


def ensure() -> None:
    if not features.features:
        features.scan()
    tools.refresh()


def default_owner(tool_name: str) -> str:
    row = tools.TOOLS.get(tool_name)
    if not row:
        return "agent"
    return row.get("agent") or priority.MODULE_OWNER.get(getattr(row["fn"], "__module__", ""), "agent")


def owner(tool_name: str) -> str:
    return control.tool_owner(tool_name) or default_owner(tool_name)


def tool_row(t: dict) -> dict:
    name = t["name"]
    return {"name": name, "description": t["description"], "args": t["args"],
            "confirm": tools.needs_confirm(name, {}) if not callable(t["confirm"]) else True,
            "conditional_confirm": callable(t["confirm"]), "always_confirm": control.tool_forced_confirm(name),
            "enabled": control.tool_enabled(name), "owner": owner(name), "default_owner": default_owner(name),
            "full_only": bool(t.get("full_only"))}


def owned(agent_id: str) -> list[dict]:
    return [tool_row(t) for t in tools.TOOLS.values() if owner(t["name"]) == agent_id]


def _desk():
    from features.desktop.desk import desk
    return desk


def widget_owner(manifest: dict) -> str:
    return control.widget_owner(manifest["id"]) or str(manifest.get("agent") or "desktop")


def widgets_of(agent_id: str) -> list[dict]:
    desk = _desk()
    return [{"id": m["id"], "name": m.get("name", m["id"]), "icon": m.get("icon", ""), "people": control.widget_people(m["id"]),
             "enabled": desk.enabled(m["id"])} for m in desk.widgets.values() if widget_owner(m) == agent_id]


def ids() -> list[str]:
    ensure()
    return sorted(features.features, key=lambda i: (-priority.of(i), i))


def settings(agent_id: str) -> list[dict]:
    values = features.settings_of(agent_id)
    rows = []
    for s in features.features[agent_id].get("settings", []):
        options = [o.get("value", o) if isinstance(o, dict) else o for o in s.get("options", [])]
        rows.append({"key": s["key"], "label": s.get("label", s["key"]), "type": s["type"], "value": values.get(s["key"], ""), "options": options})
    return rows


def profile(agent_id: str) -> dict:
    ensure()
    if agent_id not in features.features:
        raise KeyError(agent_id)
    m = features.features[agent_id]
    state = features.evaluate().get(agent_id, {})
    return {"id": agent_id, "name": m["name"], "icon": m.get("icon", ""), "category": m.get("category", "altro"),
            "source": m.get("source", "system"), "priority": priority.of(agent_id), "default_priority": priority.base(agent_id),
            "enabled": bool(state.get("enabled")), "reason": state.get("reason", ""), "toggle": bool(m.get("toggle")),
            "mode": str(state.get("mode", "")), "fixed": bool(state.get("fixed")),
            "description": m.get("description", ""), "can": list(m.get("capabilities", [])), "settings": settings(agent_id), "tools": owned(agent_id),
            "widgets": widgets_of(agent_id), "instructions": control.instructions(agent_id),
            "doing": board.current().get(agent_id, {}).get("what", ""), "inbox": len(board.inbox.get(agent_id, []))}


def find(text: str) -> str:
    ensure()
    wanted = str(text or "").strip().lower()
    if wanted in features.features:
        return wanted
    for fid, m in features.features.items():
        if wanted and wanted in m["name"].lower():
            return fid
    raise KeyError(f"agente «{text}» sconosciuto")


def one_line(agent_id: str, compact: bool = False) -> str:
    p = profile(agent_id)
    tool_names = ", ".join(t["name"] for t in p["tools"] if t["enabled"])
    doing = f" [ora: {p['doing']}]" if p["doing"] else ""
    off = "" if p["enabled"] else " [SPENTO]"
    if compact and not p["enabled"]:
        return f"- {agent_id} «{p['name']}»{off}"
    about = p["description"].split(".")[0][:SHORT // 2 if compact else SHORT]
    rules = f" Istruzioni del proprietario: {p['instructions'][:300]}" if p["instructions"] else ""
    return f"- {agent_id} «{p['name']}» p{p['priority']}{off}: {about}" + (f" Strumenti: {tool_names}." if tool_names else "") + rules + doing


def team_text(compact: bool = False, subset_ids: set[str] | None = None) -> str:
    return "\n".join(one_line(i, compact) for i in ids() if subset_ids is None or i in subset_ids)


def document() -> dict:
    return {"agents": [profile(i) for i in ids()], "doing": board.current(), "messages": list(board.messages)[-40:],
            "claims": {k: v["agent"] for k, v in board.claims.items()}}
