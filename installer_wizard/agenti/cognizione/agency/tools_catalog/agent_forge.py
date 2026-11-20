import json
from pathlib import Path

from agenti.agency.office import register_agent_widget
from agenti.agency.tools import Context, Tool, _text
from agenti.agency.tools_catalog import automations

TOOLS_CATALOG_DIR = Path(__file__).resolve().parent


async def _agent_create_automation(ctx: Context, args: dict) -> str:
    trigger = _text(args, "trigger_event", 300)
    action = _text(args, "action_payload", 300)
    desc = _text(args, "description", 300, required=False)

    automation_record = automations.create_automation(trigger, action, desc or f"Automazione forgiata dall'agente {ctx.worker or 'specialist'}")

    res = {
        "status": "automation_created_by_agent",
        "creator_agent": ctx.worker or "specialist",
        "automation": automation_record,
    }
    return json.dumps(res, ensure_ascii=False)


async def _agent_forge_tool(ctx: Context, args: dict) -> str:
    name = _text(args, "tool_name", 60)
    description = _text(args, "description", 300)
    tool_args = args.get("args") or {}
    code_content = args.get("code_content") or ""

    clean_name = name.lower().replace("-", "_").strip()
    target_file = TOOLS_CATALOG_DIR / f"{clean_name}.py"

    if not code_content:
        code_content = (
            f"import json\n"
            f"from agenti.agency.tools import Context, Tool, _text\n\n"
            f"async def _{clean_name}(ctx: Context, args: dict) -> str:\n"
            f"    return json.dumps({{'status': 'executed', 'tool': '{clean_name}', 'received_args': args}}, ensure_ascii=False)\n\n"
            f"TOOLS = {{\n"
            f"    '{clean_name}': Tool(\n"
            f"        name='{clean_name}',\n"
            f"        description='{description}',\n"
            f"        args={json.dumps(tool_args)},\n"
            f"        capability='domain_task',\n"
            f"        run=_{clean_name},\n"
            f"    )\n"
            f"}}\n"
        )

    target_file.write_text(code_content, encoding="utf-8")

    res = {
        "status": "tool_forged_by_agent",
        "creator_agent": ctx.worker or "specialist",
        "tool_name": clean_name,
        "path": str(target_file),
    }
    return json.dumps(res, ensure_ascii=False)


async def _agent_forge_widget(ctx: Context, args: dict) -> str:
    agent_id = _text(args, "agent_id", 60)
    widget_id = _text(args, "widget_id", 80)
    title = _text(args, "title", 120)
    widget_type = str(args.get("widget_type") or "domain_card").strip()
    glow = str(args.get("glow_color") or "cyan").strip()

    widget_dict = {
        "id": widget_id,
        "type": widget_type,
        "title": title,
        "creator_agent": agent_id,
        "style": "borderless_glassmorphic",
        "visual": {
            "border": "none",
            "background": "transparent",
            "backdrop_filter": "blur(16px)",
            "glow": glow,
        },
        "data_bindings": args.get("data_bindings") or {},
    }

    register_agent_widget(agent_id, widget_dict)

    res = {
        "status": "widget_forged_and_mounted",
        "agent_id": agent_id,
        "widget": widget_dict,
    }
    return json.dumps(res, ensure_ascii=False)


TOOLS = {
    "agent_create_automation": Tool(
        name="agent_create_automation",
        description="Permette a qualsiasi agente specialistico di creare e attivare un'automazione persistente per il proprio dominio.",
        args={"trigger_event": "string", "action_payload": "string", "description": "optional string"},
        capability="write",
        run=_agent_create_automation,
    ),
    "agent_forge_tool": Tool(
        name="agent_forge_tool",
        description="Permette a qualsiasi agente di creare, testare e registrare un nuovo strumento operativo per l'intero swarm.",
        args={"tool_name": "string", "description": "string", "args": "optional object", "code_content": "optional string"},
        capability="write",
        run=_agent_forge_tool,
    ),
    "agent_forge_widget": Tool(
        name="agent_forge_widget",
        description="Permette a qualsiasi agente di forgiare un widget elegante, moderno, senza contorni né sfondi, montandolo alla propria postazione.",
        args={"agent_id": "string", "widget_id": "string", "title": "string", "widget_type": "optional string", "glow_color": "optional string", "data_bindings": "optional object"},
        capability="write",
        run=_agent_forge_widget,
    ),
}
