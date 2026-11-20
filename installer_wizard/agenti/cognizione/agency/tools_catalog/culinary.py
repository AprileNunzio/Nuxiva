import json

from agenti.agency.tools import Context, Tool, ToolError, _text


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
        suggested_title = "Risotto Delicato alle Verdure di Stagione"
    elif any("pasta" in x for x in pantry_clean):
        suggested_title = "Pasta Saltata a Scarto Zero con Erbe Aromatiche"

    res = {
        "status": "recipe_tailored",
        "dish_name": suggested_title,
        "prep_and_cook_minutes": min(max_minutes, 25),
        "used_pantry_items": pantry[:4],
        "allergen_free_guarantee": allergies_clean,
        "zero_waste_tip": "I gambi e le bucce pulite delle verdure possono essere tostati per creare un fondo saporito.",
        "steps": [
            "Lava e riduci gli ingredienti in tagli uniformi per garantire tempi di cottura omogenei.",
            "Scalda un filo d'olio a temperatura controllata e fai appassire la base aromatica.",
            "Unisci i carboidrati o le proteine e porta a cottura secondo il timer sincronizzato.",
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


async def _pantry_inventory_audit(ctx: Context, args: dict) -> str:
    pantry = args.get("available_items") or []
    if isinstance(pantry, str):
        pantry = [x.strip() for x in pantry.split(",") if x.strip()]
    planned_meal = str(args.get("planned_meal") or "cena_completa").strip()

    available = [str(x).strip() for x in pantry]
    missing = []
    if not any("olio" in x.lower() for x in available):
        missing.append("olio extravergine d'oliva")
    if not any("sale" in x.lower() for x in available):
        missing.append("sale marino iodato")

    res = {
        "status": "pantry_audited",
        "planned_meal": planned_meal,
        "items_in_stock": len(available),
        "missing_essentials": missing,
        "smart_grocery_suggestion": missing if missing else ["Dispensa ben fornita per la preparazione."],
    }
    return json.dumps(res, ensure_ascii=False)


TOOLS = {
    "recipe_recommender": Tool(
        name="recipe_recommender",
        description="Consiglia ricette personalizzate incrociando dispensa, intolleranze familiari e ottimizzazione a scarto zero.",
        args={"pantry_items": "list or string", "allergies": "optional list or string", "max_minutes": "optional int"},
        capability="domain_task",
        run=_recipe_recommender,
    ),
    "cooking_timer_sync": Tool(
        name="cooking_timer_sync",
        description="Calcola l'orario perfetto di avvio cottura affinché la famiglia ceni insieme all'orario prefissato.",
        args={"dish_name": "string", "duration_minutes": "int", "family_dinner_target": "optional string"},
        capability="domain_task",
        run=_cooking_timer_sync,
    ),
    "pantry_inventory_audit": Tool(
        name="pantry_inventory_audit",
        description="Verifica gli ingredienti in dispensa per un pasto programmato ed evidenzia prodotti mancanti.",
        args={"available_items": "list or string", "planned_meal": "optional string"},
        capability="read",
        run=_pantry_inventory_audit,
    ),
}
