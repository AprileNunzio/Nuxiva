import json

from agenti.agency.self_healing import healing_governor
from agenti.agency.tools import Context, Tool, _text


async def _diagnose_and_repair_tool(ctx: Context, args: dict) -> str:
    tool_name = _text(args, "tool_name", 80)
    error_msg = _text(args, "error_message", 1000)
    snippet = args.get("patch_code_snippet")

    diagnosis = healing_governor.diagnose_failure(tool_name, error_msg)
    repair = healing_governor.synthesize_and_apply_patch(diagnosis["incident_id"], snippet)

    res = {
        "status": "self_healing_completed",
        "diagnosis": diagnosis,
        "repair": repair,
    }
    return json.dumps(res, ensure_ascii=False)


async def _verify_tool_health(ctx: Context, args: dict) -> str:
    tool_name = _text(args, "tool_name", 80)
    status_info = healing_governor.tool_status(tool_name)
    return json.dumps(status_info, ensure_ascii=False)


TOOLS = {
    "diagnose_and_repair_tool": Tool(
        name="diagnose_and_repair_tool",
        description="Diagnostica ed applica autonomamente una hotpatch quando un'API esterna cambia formato o fallisce.",
        args={"tool_name": "string", "error_message": "string", "patch_code_snippet": "optional string"},
        capability="write",
        run=_diagnose_and_repair_tool,
    ),
    "verify_tool_health": Tool(
        name="verify_tool_health",
        description="Verifica lo stato di salute di uno strumento operativo e le eventuali hotpatch attive.",
        args={"tool_name": "string"},
        capability="read",
        run=_verify_tool_health,
    ),
}
