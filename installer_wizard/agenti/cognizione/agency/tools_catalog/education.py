import json

from agenti.agency.tools import Context, Tool, ToolError, _text

DIDACTIC_PROFILES = {
    "primaria": {"tone": "giocoso e rassicurante", "depth": "esempi pratici e metafore quotidiane"},
    "media": {"tone": "incoraggiante e metodico", "depth": "regole base, formule e collegamenti logici"},
    "superiore": {"tone": "rigoroso e stimolante", "depth": "dimostrazioni, metodo scientifico e sintesi critica"},
    "universita": {"tone": "accademico ed euristico", "depth": "astrazione formale, controesempi e teoremi"},
}


async def _socratic_tutor_guide(ctx: Context, args: dict) -> str:
    topic = _text(args, "topic", 120)
    query = _text(args, "student_query", 500)
    grade = str(args.get("grade_level") or "media").strip().lower()

    profile = DIDACTIC_PROFILES.get(grade, DIDACTIC_PROFILES["media"])

    questions = [
        f"Qual è l'obiettivo centrale del problema su «{topic}» e quali sono le informazioni certe che il testo ti fornisce?",
        f"Con tono {profile['tone']}, pensa a come useresti la regola fondamentale collegata a questo contesto: quale proprietà ti viene in mente?",
        "Se provi ad applicare il primo passaggio isolando un termine o un concetto, cosa ottieni come equazione o sintesi provvisoria?",
    ]

    res = {
        "status": "socratic_guide_ready",
        "method": "maieutica_socratica",
        "topic": topic,
        "grade_level": grade,
        "pedagogical_tone": profile["tone"],
        "student_query": query,
        "guiding_questions": questions,
        "encouragement": "Procedi un elemento alla volta: hai tutti gli strumenti cognitivi per arrivare alla soluzione da solo.",
        "direct_solution_revealed": False,
    }
    return json.dumps(res, ensure_ascii=False)


async def _homework_progress_tracker(ctx: Context, args: dict) -> str:
    slug = _text(args, "student_slug", 60)
    subject = _text(args, "subject", 80)
    status = _text(args, "status", 40)
    notes = str(args.get("notes") or "").strip()
    completion_pct = int(args.get("completion_percentage") or 50)

    res = {
        "status": "recorded",
        "student": slug,
        "subject": subject,
        "progress_status": status,
        "completion_percentage": max(0, min(100, completion_pct)),
        "notes": notes,
        "study_streak_maintained": True,
    }
    return json.dumps(res, ensure_ascii=False)


async def _concept_simplifier(ctx: Context, args: dict) -> str:
    concept = _text(args, "concept", 120)
    target_age = int(args.get("target_age") or 12)

    analogy = f"Immagina «{concept}» come un ingranaggio di un orologio o come una squadra sportiva dove ogni elemento collabora."
    if target_age <= 9:
        analogy = f"Pensa a «{concept}» come a dei mattoncini colorati di un castello: se ne togli uno, l'intera torre si sposta."

    res = {
        "status": "simplified",
        "concept": concept,
        "target_age": target_age,
        "intuitive_analogy": analogy,
        "core_principle": f"Il nucleo fondamentale di {concept} spiegato senza gergo astratto.",
    }
    return json.dumps(res, ensure_ascii=False)


TOOLS = {
    "socratic_tutor_guide": Tool(
        name="socratic_tutor_guide",
        description="Genera domande guida maieutiche socratiche per aiutare studenti e figli nello studio senza svelare la soluzione.",
        args={"topic": "string", "student_query": "string", "grade_level": "optional string"},
        capability="domain_task",
        run=_socratic_tutor_guide,
    ),
    "homework_progress_tracker": Tool(
        name="homework_progress_tracker",
        description="Traccia l'avanzamento dei compiti, lo stato e le materie completate per ogni studente.",
        args={"student_slug": "string", "subject": "string", "status": "string", "completion_percentage": "optional int", "notes": "optional string"},
        capability="write",
        run=_homework_progress_tracker,
    ),
    "concept_simplifier": Tool(
        name="concept_simplifier",
        description="Spiega concetti complessi tramite analogie intuitive calibrate sull'età dello studente.",
        args={"concept": "string", "target_age": "optional int"},
        capability="domain_task",
        run=_concept_simplifier,
    ),
}
