from agenti._study import Exercise
from agenti.particles import codec, forma_design, forma_inspect

TOPICS = ("objects",)
MIN_PARTS = (1, 3, 5, 7, 9, 11, 13, 15, 17, 19)
LADDER = (
    ("sfera", "cubo", "colonna"),
    ("tavolo", "fungo", "ombrello"),
    ("gatto", "pesce", "uccello"),
    ("cavallo", "farfalla", "serpente"),
    ("bicicletta", "faro", "ponte"),
    ("automobile", "barca a vela", "aeroplano"),
    ("locomotiva", "motore a pistoni", "castello"),
    ("elicottero", "turbina", "cattedrale"),
    ("sistema solare", "galassia a spirale", "nave spaziale"),
    ("orologio meccanico", "stazione spaziale", "cellula con organelli"),
)


def make(topic: str, tier: int) -> Exercise:
    names = LADDER[min(max(tier, 0), len(LADDER) - 1)]
    return Exercise(topic, tier, names[0], {"names": names})


async def attempt(exercise: Exercise):
    return await forma_design.create(exercise.prompt)


def grade(exercise: Exercise, result) -> tuple[float, str]:
    if not isinstance(result, dict):
        return 0.0, f"{exercise.prompt}: nessuna forma prodotta"
    spec = codec.validate(result)
    parts = spec["parts"]
    report = forma_inspect.report(parts, 1.0)
    need = MIN_PARTS[min(exercise.tier, len(MIN_PARTS) - 1)]
    detail = 0.4 * min(1.0, len(parts) / need)
    joined = 0.4 if "detached_parts" not in report["issues"] else 0.4 / max(1, report["components"])
    solid = 0.2 if "flat" not in report["issues"] else 0.0
    score = round(detail + joined + solid, 4)
    lesson = ""
    if report["issues"]:
        lesson = f"{exercise.prompt}: {', '.join(report['issues'])}, parti {len(parts)} su {need} richieste"
    return score, lesson
