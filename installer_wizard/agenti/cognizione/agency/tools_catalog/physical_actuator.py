import json

from agenti.agency.physical_actuation import ActuationCommand, physical_actuator
from agenti.agency.tools import Context, Tool, _text


async def _set_room_preset_scene(ctx: Context, args: dict) -> str:
    scene_name = _text(args, "scene_name", 80)
    room_id = str(args.get("room_id") or "default_room").strip()
    res = physical_actuator.apply_preset_scene(scene_name, room_id)
    return json.dumps(res, ensure_ascii=False)


async def _dispatch_physical_command(ctx: Context, args: dict) -> str:
    domain = _text(args, "domain", 40)
    target_id = _text(args, "target_id", 80)
    action = _text(args, "action", 40)
    params = args.get("parameters") or {}
    room_id = str(args.get("room_id") or "default_room").strip()

    cmd = ActuationCommand(
        domain=domain,
        target_id=target_id,
        action=action,
        parameters=params,
        room_id=room_id,
    )
    res = physical_actuator.execute_command(cmd)
    return json.dumps(res, ensure_ascii=False)


TOOLS = {
    "set_room_preset_scene": Tool(
        name="set_room_preset_scene",
        description="Applica preset ambientali fisici completi alla stanza (focus_work_office, socratic_study_mode, chef_cooking_preset, bedtime_calm_dreamscape, co_presence_privacy_lockdown).",
        args={"scene_name": "string", "room_id": "optional string"},
        capability="execute",
        run=_set_room_preset_scene,
    ),
    "dispatch_physical_command": Tool(
        name="dispatch_physical_command",
        description="Invia comandi attuativi fisici granulari (luci, termostati, audio, prese) attraverso il bus unificato Matter/Home Assistant/Zigbee.",
        args={"domain": "string", "target_id": "string", "action": "string", "parameters": "optional object", "room_id": "optional string"},
        capability="execute",
        run=_dispatch_physical_command,
    ),
}
