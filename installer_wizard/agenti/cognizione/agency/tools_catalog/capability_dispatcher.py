import json

from agenti.agency.on_demand_forge import on_demand_governor
from agenti.agency.tools import Context, Tool, _text


async def _dispatch_capability_request(ctx: Context, args: dict) -> str:
    query = _text(args, "query", 300)
    person_slug = str(args.get("person_slug") or "ospite").strip()
    channel = str(args.get("channel") or "voice").strip()
    lang = str(args.get("lang") or "it").strip()

    res = on_demand_governor.request_capability(
        user_query=query,
        person_slug=person_slug,
        channel=channel,
        lang=lang,
    )
    return json.dumps(res, ensure_ascii=False)


async def _notify_capability_completed(ctx: Context, args: dict) -> str:
    cap_name = _text(args, "capability_name", 80)
    artifact = args.get("artifact_data") or {}
    ready_msg = str(args.get("custom_ready_message") or "").strip()

    res = on_demand_governor.complete_forge(
        capability_name=cap_name,
        artifact_data=artifact,
        custom_ready_message=ready_msg,
    )
    return json.dumps(res, ensure_ascii=False)


TOOLS = {
    "dispatch_capability_request": Tool(
        name="dispatch_capability_request",
        description="Gestisce qualsiasi richiesta utente per giochi, app o strumenti inediti: verifica la presenza, commissiona la creazione asincrona al CEO e risponde istantaneamente all'utente proponendo la notifica al completamento.",
        args={"query": "string", "person_slug": "optional string", "channel": "optional string", "lang": "optional string"},
        capability="execute",
        run=_dispatch_capability_request,
    ),
    "notify_capability_completed": Tool(
        name="notify_capability_completed",
        description="Notifica il completamento e il collaudo di una capacità forgiata dal CEO, emettendo la notifica proattiva verso gli utenti in attesa.",
        args={"capability_name": "string", "artifact_data": "optional object", "custom_ready_message": "optional string"},
        capability="write",
        run=_notify_capability_completed,
    ),
}
