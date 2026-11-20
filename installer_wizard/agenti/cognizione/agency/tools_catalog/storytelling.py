import json

from agenti.agency.tools import Context, Tool, _text


async def _generate_bedtime_story(ctx: Context, args: dict) -> str:
    child_name = _text(args, "child_name", 60)
    theme = str(args.get("theme") or "un viaggio tra le stelle amiche").strip()
    moral = str(args.get("moral") or "il valore della gentilezza e dell'ascolto").strip()
    calming_level = int(args.get("calming_level") or 5)

    story_text = (
        f"C'era una volta, in una valle dove le lucciole danzavano leggere, un piccolo esploratore di nome {child_name}. "
        f"Un giorno decise di seguire il sentiero dorato verso {theme}. Camminando piano piano, imparò che {moral}. "
        "E mentre la luna stendeva un soffice mantello di stelle sul mondo intero, gli occhietti si fecero pesanti e felici... Buonanotte."
    )

    res = {
        "status": "story_generated",
        "child_name": child_name,
        "theme": theme,
        "calming_level": max(1, min(10, calming_level)),
        "story": story_text,
        "ambient_preset": {
            "lighting": "warm_amber_15_percent",
            "tempo_deceleration": "80_bpm_to_55_bpm",
            "ambient_sound": "gentle_crickets_and_distant_waves",
        },
    }
    return json.dumps(res, ensure_ascii=False)


async def _ambient_bedtime_preset(ctx: Context, args: dict) -> str:
    room = str(args.get("room") or "cameretta").strip()
    target_sleep_minutes = int(args.get("transition_minutes") or 20)

    res = {
        "status": "bedtime_preset_engaged",
        "target_room": room,
        "transition_minutes": target_sleep_minutes,
        "light_color": "#ff9933",
        "brightness_start": 30,
        "brightness_end": 5,
        "soundtrack": "white_noise_rain_filtered",
        "volume_ramp": "step_down_every_4_minutes",
    }
    return json.dumps(res, ensure_ascii=False)


TOOLS = {
    "generate_bedtime_story": Tool(
        name="generate_bedtime_story",
        description="Genera fiabe personalizzate della buonanotte con ritmo vocale e atmosfera rassicuranti.",
        args={"child_name": "string", "theme": "optional string", "calming_level": "optional int", "moral": "optional string"},
        capability="domain_task",
        run=_generate_bedtime_story,
    ),
    "ambient_bedtime_preset": Tool(
        name="ambient_bedtime_preset",
        description="Imposta la transizione multisensoriale di camera da letto per accompagnare il sonno dei bambini.",
        args={"room": "optional string", "transition_minutes": "optional int"},
        capability="domain_task",
        run=_ambient_bedtime_preset,
    ),
}
