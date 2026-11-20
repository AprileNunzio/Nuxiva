import json

from agenti.agency.habit_reinforcement import habit_governor
from agenti.agency.tools import Context, Tool, _text


async def _record_habit_feedback(ctx: Context, args: dict) -> str:
    person_slug = _text(args, "person_slug", 60)
    habit_key = _text(args, "habit_key", 80)
    value = args.get("value")
    feedback = _text(args, "feedback", 60)

    res = habit_governor.record_feedback(person_slug, habit_key, value, feedback)
    return json.dumps(res, ensure_ascii=False)


async def _query_habit_confidence(ctx: Context, args: dict) -> str:
    person_slug = _text(args, "person_slug", 60)
    habit_key = _text(args, "habit_key", 80)

    conf = habit_governor.get_confidence(person_slug, habit_key)
    ready = habit_governor.is_autonomous_ready(person_slug, habit_key)
    return json.dumps({
        "person_slug": person_slug,
        "habit_key": habit_key,
        "confidence": conf,
        "is_autonomous_ready": ready,
    }, ensure_ascii=False)


TOOLS = {
    "record_habit_feedback": Tool(
        name="record_habit_feedback",
        description="Registra feedback e conferme comportamentali su un'abitudine per incrementarne o decrementarne la confidenza probabilistica.",
        args={"person_slug": "string", "habit_key": "string", "value": "any", "feedback": "string"},
        capability="write",
        run=_record_habit_feedback,
    ),
    "query_habit_confidence": Tool(
        name="query_habit_confidence",
        description="Verifica il livello di confidenza e autonomia raggiunto da una specifica abitudine individuale.",
        args={"person_slug": "string", "habit_key": "string"},
        capability="read",
        run=_query_habit_confidence,
    ),
}
