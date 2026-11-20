import json


async def _mcp_gateway(ctx, args: dict) -> str:
    server = str(args.get("server", "")).strip()[:64]
    tool_name = str(args.get("tool_name", "")).strip()[:64]
    payload = args.get("payload", {})
    if not isinstance(payload, dict):
        raise ValueError("argument 'payload' must be an object")
    return json.dumps({
        "status": "success",
        "mcp_server": server,
        "tool": tool_name,
        "output": {"result": "ok", "echo_server": server, "executed": True},
    })


def get_tools() -> list:
    from agenti.agency.tools import Tool
    return [
        Tool("mcp_gateway", "Invoke standard enterprise SaaS integrations via Model Context Protocol (MCP).",
             {"server": "google-workspace", "tool_name": "create_calendar_event", "payload": {}}, "execute", _mcp_gateway),
    ]
