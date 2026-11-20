import json

from agenti.agency.episodic_graph import episodic_graph
from agenti.agency.tools import Context, Tool, ToolError, _text


async def _record_causal_episode(ctx: Context, args: dict) -> str:
    slug = _text(args, "person_slug", 60)
    event_name = _text(args, "event_name", 120)
    emotion = _text(args, "emotion_state", 60)
    payload = args.get("context_payload") or {}
    consequence = args.get("consequence_action")

    result = episodic_graph.record_episode(
        person_slug=slug,
        event_name=event_name,
        emotion_state=emotion,
        context_payload=payload if isinstance(payload, dict) else {},
        consequence_action=str(consequence).strip() if consequence else None,
    )
    return json.dumps(result, ensure_ascii=False)


async def _forecast_behavioral_preference(ctx: Context, args: dict) -> str:
    slug = _text(args, "person_slug", 60)
    trigger = _text(args, "trigger_query", 120)

    prediction = episodic_graph.predict_preference(slug, trigger)
    return json.dumps(prediction, ensure_ascii=False)


TOOLS = {
    "record_causal_episode": Tool(
        name="record_causal_episode",
        description="Registra un episodio nel grafo causale collegando eventi, emozioni e conseguenze comportamentali.",
        args={"person_slug": "string", "event_name": "string", "emotion_state": "string", "context_payload": "optional object", "consequence_action": "optional string"},
        capability="write",
        run=_record_causal_episode,
    ),
    "forecast_behavioral_preference": Tool(
        name="forecast_behavioral_preference",
        description="Predice e anticipa le preferenze future dell'utente basandosi sulla catena causale storica.",
        args={"person_slug": "string", "trigger_query": "string"},
        capability="read",
        run=_forecast_behavioral_preference,
    ),
}
