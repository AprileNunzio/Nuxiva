import json
import re

from agenti.agency.circadian import resolve_circadian_context
from agenti.agency.tools import Context, Tool, ToolError, _text
from agenti.people import learning, people, schema


async def _get_person_profile(ctx: Context, args: dict) -> str:
    slug = _text(args, "slug", 60)
    p = people.load(slug)
    if not p:
        return json.dumps({"status": "not_found", "slug": slug, "message": f"Persona {slug} non trovata nell'applicazione persone"})
    res = {
        "slug": p.get("slug"),
        "name": people.display_name(p),
        "nickname": p.get("nickname"),
        "role": p.get("role"),
        "passions": p.get("hobbies") or [],
        "tastes": {
            "food_likes": p.get("food_likes") or [],
            "food_dislikes": p.get("food_dislikes") or [],
            "drinks": p.get("drinks") or [],
            "coffee": p.get("coffee") or "",
            "music": p.get("music") or [],
            "movies": p.get("movies") or [],
            "books": p.get("books") or [],
            "sports": p.get("sports") or [],
            "temperature": p.get("temperature"),
        },
        "habits": {
            "wake_time": p.get("wake_time"),
            "sleep_time": p.get("sleep_time"),
            "daily_habits": p.get("daily_habits") or [],
            "quiet_hours": p.get("quiet_hours") or "",
            "routines": p.get("routines") or [],
        },
        "summary": people.context_for([slug]),
    }
    return json.dumps(res, ensure_ascii=False)


async def _update_person_preference(ctx: Context, args: dict) -> str:
    slug = _text(args, "slug", 60)
    field = _text(args, "field", 60)
    raw_val = args.get("value")
    if raw_val is None:
        raise ToolError("argument 'value' is required")
    name = args.get("name") or slug.replace("-", " ").title()
    profile = people.load(slug)
    if not profile:
        profile = people.ensure(slug, name)

    field_def = schema.FIELD_INDEX.get(field)
    val = raw_val
    if field_def and field_def[1]["type"] == "tags":
        if isinstance(raw_val, str):
            val = [x.strip() for x in raw_val.split(",") if x.strip()]
        elif isinstance(raw_val, list):
            val = [str(x).strip() for x in raw_val if str(x).strip()]

    people.update(slug, {field: val})
    return json.dumps({
        "status": "saved",
        "slug": slug,
        "field": field,
        "value": val,
        "storage": "agenti.people",
    }, ensure_ascii=False)


async def _perceive_multimodal_person(ctx: Context, args: dict) -> str:
    visual_cue = str(args.get("visual_cue") or "").strip()
    audio_cue = str(args.get("audio_cue") or "").strip()
    spoken_text = str(args.get("spoken_text") or "").strip()
    explicit_slug = str(args.get("person_slug") or "").strip().lower()

    detected_slug = explicit_slug
    if not detected_slug:
        combined = f"{visual_cue} {audio_cue} {spoken_text}".lower()
        for p in people.all_profiles(light=True):
            cand_slug = p.get("slug", "").lower()
            cand_name = (p.get("first_name") or p.get("name") or "").lower()
            if cand_slug and cand_slug in combined:
                detected_slug = cand_slug
                break
            if cand_name and len(cand_name) >= 3 and cand_name in combined:
                detected_slug = cand_slug
                break

    if not detected_slug:
        detected_slug = "ospite"

    name = detected_slug.replace("-", " ").title()
    p = people.load(detected_slug)
    if not p:
        p = people.ensure(detected_slug, name)

    people.observe(detected_slug, name)

    learned_observations = []
    if spoken_text:
        res = learning.observe(spoken_text, detected_slug)
        learned_observations.append({"type": "spoken_observation", "data": res})

    if "stanco" in visual_cue.lower():
        learning.learn_mood(detected_slug, "oggi sono stanco")
    elif "sorridente" in visual_cue.lower() or "felice" in visual_cue.lower():
        learning.learn_mood(detected_slug, "oggi sono felice")

    circadian_state = resolve_circadian_context(person_slug=detected_slug)

    return json.dumps({
        "status": "perceived",
        "active_person": detected_slug,
        "visual_cue": visual_cue,
        "audio_cue": audio_cue,
        "spoken_text": spoken_text,
        "learned": learned_observations,
        "circadian_context": circadian_state,
    }, ensure_ascii=False)


TOOLS = {
    "get_person_profile": Tool(
        name="get_person_profile",
        description="Recupera abitudini, passioni, gusti e preferenze di una persona dall'applicazione persone.",
        args={"slug": "string identifying the person"},
        capability="read",
        run=_get_person_profile,
    ),
    "update_person_preference": Tool(
        name="update_person_preference",
        description="Salva o aggiorna un'abitudine, passione o gusto direttamente nella scheda della persona nell'applicazione persone.",
        args={"slug": "string", "field": "string", "value": "value or list", "name": "optional string"},
        capability="write",
        run=_update_person_preference,
    ),
    "perceive_multimodal_person": Tool(
        name="perceive_multimodal_person",
        description="Elabora stimoli multimodali (visivi e uditivi) per identificare la persona, apprendere nuove abitudini e personalizzare il contesto circadiano.",
        args={"visual_cue": "optional string", "audio_cue": "optional string", "spoken_text": "optional string", "person_slug": "optional string"},
        capability="domain_task",
        run=_perceive_multimodal_person,
    ),
}
