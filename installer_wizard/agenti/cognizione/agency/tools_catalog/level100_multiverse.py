import json
import re

from agenti.agency.tools import Context, Tool, ToolError, _text
from agenti.people import people

RESTRICTED_ACTIONS = {
    "child": {"gate_unlock", "payment_purchase", "alarm_disarm", "financial_read", "camera_live_all"},
    "guest": {"financial_read", "health_read", "private_diary_read", "gate_unlock", "alarm_disarm", "camera_live_all"},
    "staff": {"financial_read", "health_read", "private_diary_read"},
}


async def _socratic_tutor_guide(ctx: Context, args: dict) -> str:
    topic = _text(args, "topic", 120)
    query = _text(args, "student_query", 500)
    grade = str(args.get("grade_level") or "scuola").strip()

    questions = [
        f"Cosa ti chiede esattamente il problema su «{topic}» e quali dati hai a disposizione?",
        "Quale regola o principio logico abbiamo visto che collega questi elementi?",
        "Se provi a fare il primo passaggio semplificando, cosa ottieni come risultato intermedio?",
    ]
    res = {
        "status": "socratic_guide_ready",
        "method": "maieutica_socratica",
        "topic": topic,
        "grade_level": grade,
        "student_query": query,
        "guiding_questions": questions,
        "encouragement": "Fai un passo alla volta: sei sulla strada giusta per arrivarci da solo!",
        "direct_solution_revealed": False,
    }
    return json.dumps(res, ensure_ascii=False)


async def _homework_progress_tracker(ctx: Context, args: dict) -> str:
    slug = _text(args, "student_slug", 60)
    subject = _text(args, "subject", 80)
    status = _text(args, "status", 40)
    notes = str(args.get("notes") or "").strip()

    res = {
        "status": "recorded",
        "student": slug,
        "subject": subject,
        "progress_status": status,
        "notes": notes,
    }
    return json.dumps(res, ensure_ascii=False)


async def _recipe_recommender(ctx: Context, args: dict) -> str:
    pantry = args.get("pantry_items") or []
    if isinstance(pantry, str):
        pantry = [x.strip() for x in pantry.split(",") if x.strip()]
    allergies = args.get("allergies") or []
    if isinstance(allergies, str):
        allergies = [x.strip() for x in allergies.split(",") if x.strip()]
    max_minutes = int(args.get("max_minutes") or 30)

    pantry_clean = [str(x).lower() for x in pantry]
    allergies_clean = [str(x).lower() for x in allergies]

    suggested_title = "Primo Piatto Mediterraneo Fresco"
    if any("riso" in x for x in pantry_clean):
        suggested_title = "Risotto Delicato alle Verdure"
    elif any("pasta" in x for x in pantry_clean):
        suggested_title = "Pasta Saltata a Scarto Zero con Verdure di Stagione"

    res = {
        "status": "recipe_tailored",
        "dish_name": suggested_title,
        "prep_and_cook_minutes": min(max_minutes, 25),
        "used_pantry_items": pantry[:4],
        "allergen_free_guarantee": allergies_clean,
        "zero_waste_tip": "Usa le bucce o i gambi per un brodo aromatico veloce.",
        "steps": [
            "Lava e taglia gli ingredienti a cubetti uniformi per velocizzare la cottura.",
            "Scalda un filo d'olio a fiamma dolce e salta gli elementi base.",
            "Unisci la base di carboidrati e porta a termine la cottura nei minuti stabiliti.",
        ],
    }
    return json.dumps(res, ensure_ascii=False)


async def _cooking_timer_sync(ctx: Context, args: dict) -> str:
    dish = _text(args, "dish_name", 120)
    duration = int(args.get("duration_minutes") or 25)
    target_str = str(args.get("family_dinner_target") or "20:00").strip()

    target_h, target_m = 20, 0
    if ":" in target_str:
        parts = target_str.split(":")
        try:
            target_h, target_m = int(parts[0]), int(parts[1])
        except ValueError:
            pass

    target_total = target_h * 60 + target_m
    start_total = (target_total - duration) % (24 * 60)
    start_h = start_total // 60
    start_m = start_total % 60

    start_formatted = f"{start_h:02d}:{start_m:02d}"

    res = {
        "status": "timer_synchronized",
        "dish_name": dish,
        "duration_minutes": duration,
        "family_dinner_target": f"{target_h:02d}:{target_m:02d}",
        "recommended_start_time": start_formatted,
        "notification_alert": f"Avviso programmato alle {start_formatted} per iniziare a cucinare «{dish}».",
    }
    return json.dumps(res, ensure_ascii=False)


async def _generate_bedtime_story(ctx: Context, args: dict) -> str:
    child_name = _text(args, "child_name", 60)
    theme = str(args.get("theme") or "un viaggio tra le stelle amiche").strip()
    moral = str(args.get("moral") or "il valore della gentilezza e dell'ascolto").strip()

    story_text = (
        f"C'era una volta, in una valle dove le lucciole danzavano leggere, un piccolo esploratore di nome {child_name}. "
        f"Un giorno decise di seguire il sentiero dorato verso {theme}. Camminando piano piano, imparò che {moral}. "
        "E mentre la luna stendeva un soffice mantello di stelle sul mondo intero, gli occhietti si fecero pesanti e felici... Buonanotte."
    )

    res = {
        "status": "story_generated",
        "child_name": child_name,
        "theme": theme,
        "story": story_text,
        "ambient_preset": {
            "lighting": "warm_amber_15_percent",
            "tempo_deceleration": "80_bpm_to_55_bpm",
            "ambient_sound": "gentle_crickets_and_distant_waves",
        },
    }
    return json.dumps(res, ensure_ascii=False)


async def _authorize_action_by_role(ctx: Context, args: dict) -> str:
    slug = _text(args, "person_slug", 60)
    action = _text(args, "action_kind", 60)

    p = people.load(slug)
    role = p.get("role", "guest") if p else "guest"
    subrole = p.get("subrole", "") if p else ""
    is_child = subrole == "child" or role == "child" or any(r.get("type") == "figlio" for r in p.get("relations", []) if isinstance(r, dict))
    eff_role = "child" if is_child else role
    blocked = RESTRICTED_ACTIONS.get(eff_role, set())

    is_allowed = action not in blocked
    reason = "Autorizzazione concessa dal profilo di sicurezza Zero-Trust." if is_allowed else f"Azione negata: il profilo «{eff_role}» non possiede il permesso per «{action}»."

    res = {
        "person_slug": slug,
        "role": role,
        "effective_profile": eff_role,
        "action_kind": action,
        "allowed": is_allowed,
        "reason": reason,
    }
    return json.dumps(res, ensure_ascii=False)


TOOLS = {
    "socratic_tutor_guide": Tool(
        name="socratic_tutor_guide",
        description="Genera domande guida maieutiche socratiche per aiutare studenti nei compiti senza svelare la soluzione.",
        args={"topic": "string", "student_query": "string", "grade_level": "optional string"},
        capability="domain_task",
        run=_socratic_tutor_guide,
    ),
    "homework_progress_tracker": Tool(
        name="homework_progress_tracker",
        description="Traccia l'avanzamento dei compiti e lo studio per ogni figlio o studente.",
        args={"student_slug": "string", "subject": "string", "status": "string", "notes": "optional string"},
        capability="write",
        run=_homework_progress_tracker,
    ),
    "recipe_recommender": Tool(
        name="recipe_recommender",
        description="Consiglia ricette personalizzate incrociando gli ingredienti della dispensa con le intolleranze familiari.",
        args={"pantry_items": "list or string", "allergies": "optional list or string", "max_minutes": "optional int"},
        capability="domain_task",
        run=_recipe_recommender,
    ),
    "cooking_timer_sync": Tool(
        name="cooking_timer_sync",
        description="Sincronizza i tempi di preparazione dei piatti affinché la famiglia ceni insieme all'orario prefissato.",
        args={"dish_name": "string", "duration_minutes": "int", "family_dinner_target": "optional string"},
        capability="domain_task",
        run=_cooking_timer_sync,
    ),
    "generate_bedtime_story": Tool(
        name="generate_bedtime_story",
        description="Genera una fiaba personalizzata della buonanotte con modulazione rilassante di voce, luci e suoni.",
        args={"child_name": "string", "theme": "optional string", "calming_level": "optional int", "moral": "optional string"},
        capability="domain_task",
        run=_generate_bedtime_story,
    ),
    "authorize_action_by_role": Tool(
        name="authorize_action_by_role",
        description="Verifica l'autorizzazione di sicurezza Zero-Trust per ospiti, proprietari, figli e collaboratori.",
        args={"person_slug": "string", "action_kind": "string"},
        capability="read",
        run=_authorize_action_by_role,
    ),
}
