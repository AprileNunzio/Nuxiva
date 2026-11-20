import json
import time

_ACTIVE_AUTOMATIONS: dict[str, dict] = {}


async def _create_automation(ctx, args: dict) -> str:
    name = str(args.get("name", "")).strip()[:120]
    if not name:
        raise ValueError("argument 'name' is required for automation")
    trigger = args.get("trigger", {})
    action = args.get("action", {})
    desc = str(args.get("description", "")).strip()[:400]
    widget = args.get("widget") or {
        "id": f"aut_{int(time.time())}",
        "type": "automation_monitor",
        "title": name,
        "trigger": trigger,
        "action": action,
        "status": "active",
    }
    record = {
        "id": f"aut_{len(_ACTIVE_AUTOMATIONS) + 1}",
        "name": name,
        "description": desc or f"Automazione autonoma: {name}",
        "trigger": trigger,
        "action": action,
        "widget": widget,
        "active": True,
        "created_at": time.time(),
        "invocations": 0,
    }
    _ACTIVE_AUTOMATIONS[name] = record
    return json.dumps({
        "status": "created",
        "automation_id": record["id"],
        "name": name,
        "trigger": trigger,
        "action": action,
        "active": True,
        "widget": widget,
    }, ensure_ascii=False)


async def _list_automations(ctx, args: dict) -> str:
    return json.dumps({"automations": list(_ACTIVE_AUTOMATIONS.values())}, ensure_ascii=False)


async def _toggle_automation(ctx, args: dict) -> str:
    name = str(args.get("name", "")).strip()
    active = bool(args.get("active", True))
    if name not in _ACTIVE_AUTOMATIONS:
        raise ValueError(f"automation '{name}' not found")
    _ACTIVE_AUTOMATIONS[name]["active"] = active
    return json.dumps({"status": "updated", "name": name, "active": active})


def get_active_automations() -> list[dict]:
    return list(_ACTIVE_AUTOMATIONS.values())


def get_tools() -> list:
    from agenti.agency.tools import Tool
    return [
        Tool("create_automation", "Create an event-driven automation flow (e.g. trigger on email/sensor and dispatch voice/message).",
             {"name": "Angelika Email Call", "trigger": {"type": "email_received", "from": "Angelika"}, "action": {"type": "twilio_call"}},
             "execute", _create_automation),
        Tool("list_automations", "List all active event-driven automations in the agency.", {}, "read", _list_automations),
        Tool("toggle_automation", "Enable or disable an existing automation.", {"name": "Angelika Email Call", "active": True}, "execute", _toggle_automation),
    ]
