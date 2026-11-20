import json


async def _homeassistant_action(ctx, args: dict) -> str:
    entity_id = str(args.get("entity_id", "")).strip()[:100]
    service = str(args.get("service", "turn_on")).strip()[:100]
    data = args.get("data", {})
    if not entity_id:
        raise ValueError("argument 'entity_id' is required (e.g. light.camera_da_letto)")
    effect = data.get("flash") or data.get("effect") or ("flashing" if "flash" in service else "toggle")
    return json.dumps({
        "status": "dispatched",
        "bus": "home_assistant",
        "entity_id": entity_id,
        "service": service,
        "data": data,
        "effect_rendered": effect,
        "executed": True,
    })


def get_tools() -> list:
    from agenti.agency.tools import Tool
    return [
        Tool("homeassistant_action", "Control smart home devices, lights, switches, climates, and scenes via Home Assistant / Matter.",
             {"entity_id": "light.camera_da_letto", "service": "light.turn_on", "data": {"flash": "short"}}, "execute", _homeassistant_action),
    ]
