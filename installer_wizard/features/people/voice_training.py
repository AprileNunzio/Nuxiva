import re
import time
import unicodedata

from features.ear.learner import name_variant
from features.people import people

MAX_TEXT = 200
MAX_ITEMS = 40
KINDS = ("wake", "command", "reading")

PLANS = {
    "it": {
        "wake": ["Nuxiva", "Nuxiva", "Nuxiva", "Hey Nuxiva", "Hey Nuxiva", "Ehi Nuxiva"],
        "command": ["Nuxiva, che ore sono?", "Nuxiva, accendi la luce del soggiorno", "Hey Nuxiva, metti un po' di musica",
                    "Nuxiva, ricordami di chiamare la mamma domani alle nove"],
        "reading": ["Buongiorno Nuxiva, oggi è una splendida giornata per imparare qualcosa di nuovo.",
                    "Vorrei sapere che tempo farà domani pomeriggio e se devo portare l'ombrello.",
                    "La mia voce è unica: da oggi mi riconoscerai anche senza guardarmi."],
    },
    "en": {
        "wake": ["Nuxiva", "Nuxiva", "Nuxiva", "Hey Nuxiva", "Hey Nuxiva", "Okay Nuxiva"],
        "command": ["Nuxiva, what time is it?", "Nuxiva, turn on the living room light", "Hey Nuxiva, play some music",
                    "Nuxiva, remind me to call mum tomorrow at nine"],
        "reading": ["Good morning Nuxiva, today is a wonderful day to learn something new.",
                    "I would like to know what the weather will be like tomorrow afternoon.",
                    "My voice is unique: from today you will recognise me even without seeing me."],
    },
    "es": {
        "wake": ["Nuxiva", "Nuxiva", "Nuxiva", "Hey Nuxiva", "Hey Nuxiva", "Oye Nuxiva"],
        "command": ["Nuxiva, ¿qué hora es?", "Nuxiva, enciende la luz del salón", "Hey Nuxiva, pon un poco de música",
                    "Nuxiva, recuérdame llamar a mamá mañana a las nueve"],
        "reading": ["Buenos días Nuxiva, hoy es un día estupendo para aprender algo nuevo.",
                    "Me gustaría saber qué tiempo hará mañana por la tarde.",
                    "Mi voz es única: desde hoy me reconocerás incluso sin verme."],
    },
    "fr": {
        "wake": ["Nuxiva", "Nuxiva", "Nuxiva", "Hey Nuxiva", "Hey Nuxiva", "Dis Nuxiva"],
        "command": ["Nuxiva, quelle heure est-il ?", "Nuxiva, allume la lumière du salon", "Hey Nuxiva, mets un peu de musique",
                    "Nuxiva, rappelle-moi d'appeler maman demain à neuf heures"],
        "reading": ["Bonjour Nuxiva, aujourd'hui est une belle journée pour apprendre quelque chose de nouveau.",
                    "J'aimerais savoir quel temps il fera demain après-midi.",
                    "Ma voix est unique : à partir d'aujourd'hui tu me reconnaîtras même sans me voir."],
    },
}


def get_assistant_name() -> str:
    from identity import assistant_name
    return assistant_name()


def stale(training: dict | None) -> bool:
    if not isinstance(training, dict) or not training:
        return False
    return str(training.get("assistant", "")).strip().lower() != get_assistant_name().strip().lower()


def language(lang: str | None) -> str:
    return lang if lang in PLANS else "it"


CONDITIONS = (
    ("wake", 0, "soft", "near"),
    ("wake", 3, "raised", "near"),
    ("wake", 0, "normal", "far"),
    ("command", 0, "normal", "far"),
    ("command", 1, "raised", "far"),
    ("command", 2, "soft", "near"),
)
TONES = ("normal", "soft", "raised")
DISTANCES = ("near", "far")


def plan(lang: str | None, custom_name: str | None = None) -> list[dict]:
    name = custom_name or get_assistant_name()
    chosen = PLANS[language(lang)]

    def fill(template: str) -> str:
        return template.replace("Nuxiva", name).replace("nuxiva", name.lower())

    out = [{"kind": kind, "text": fill(template), "tone": "normal", "distance": "near"}
           for kind in KINDS for template in chosen[kind]]
    for kind, index, tone, distance in CONDITIONS:
        out.append({"kind": kind, "text": fill(chosen[kind][index]), "tone": tone, "distance": distance})
    return out


def plain(text: str) -> str:
    folded = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in folded if unicodedata.category(c) != "Mn")


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", plain(text))


def similarity(expected: str, heard: str) -> float:
    want, got = set(words(expected)), set(words(heard))
    return len(want & got) / len(want) if want else 0.0


def evaluate(item: dict, heard: str) -> dict:
    kind, said = item["kind"], item["text"]
    heard = " ".join(str(heard or "").split())[:MAX_TEXT]
    variant = name_variant(heard) if kind in ("wake", "command") else None
    if kind == "wake":
        ok = variant is not None
    elif kind == "command":
        ok = variant is not None and similarity(said, heard) >= 0.5
    else:
        ok = bool(heard)
    return {"kind": kind, "said": said, "heard": heard, "ok": ok, "variant": variant,
            "tone": item.get("tone", "normal"), "distance": item.get("distance", "near")}


def condition_key(result: dict) -> str:
    return f"{result.get('tone', 'normal')}_{result.get('distance', 'near')}"


def summarize(results: list, levels: list) -> tuple[dict, list]:
    groups: dict[str, dict] = {}
    for result, level in zip(results, levels):
        group = groups.setdefault(condition_key(result), {"ok": 0, "total": 0, "rms": 0.0})
        group["total"] += 1
        group["ok"] += int(result["ok"])
        group["rms"] += level["rms"]
    for group in groups.values():
        group["rms"] = round(group["rms"] / group["total"], 4)
    tips = []
    far = [g for k, g in groups.items() if k.endswith("_far")]
    soft = [g for k, g in groups.items() if k.startswith("soft_")]
    if far and sum(g["ok"] for g in far) < 0.6 * sum(g["total"] for g in far):
        tips.append("far_weak")
    if soft and sum(g["ok"] for g in soft) < 0.6 * sum(g["total"] for g in soft):
        tips.append("soft_weak")
    base = groups.get("normal_near")
    if base and base["rms"] < 0.015:
        tips.append("mic_low")
    if any(lv["clipping"] > 0.02 for lv in levels):
        tips.append("clipping")
    return groups, tips


def _clean_level(level) -> dict:
    level = level if isinstance(level, dict) else {}
    out = {}
    for key in ("rms", "peak", "clipping"):
        try:
            out[key] = round(min(1.0, max(0.0, float(level.get(key, 0)))), 4)
        except (TypeError, ValueError):
            out[key] = 0.0
    advice = level.get("advice")
    out["advice"] = advice if advice in ("ok", "lower", "raise") else "ok"
    return out


def record(slug: str, lang: str | None, answers: list) -> dict:
    profile = people.load(slug)
    if not profile:
        raise LookupError(slug)
    items = plan(lang)
    if not isinstance(answers, list) or not answers or len(answers) > MAX_ITEMS:
        raise ValueError("Risultati dell'addestramento non validi")
    results, levels = [], []
    for answer in answers:
        if not isinstance(answer, dict) or not isinstance(answer.get("index"), int) or not 0 <= answer["index"] < len(items):
            raise ValueError("Risultati dell'addestramento non validi")
        results.append(evaluate(items[answer["index"]], str(answer.get("heard") or "")))
        levels.append(_clean_level(answer.get("level")))
    variants = sorted({r["variant"] for r in results if r["variant"]})
    spoken = [r for r in results if r["kind"] in ("wake", "command")]
    dictionary = [{"said": r["said"], "heard": r["heard"]} for r in spoken if r["heard"] and plain(r["heard"]) != plain(r["said"])]
    conditions, tips = summarize(results, levels)
    profile["voice_training"] = {
        "trained_at": time.time(),
        "language": language(lang),
        "score": round(100 * sum(r["ok"] for r in results) / len(results)),
        "wake_variants": variants,
        "dictionary": dictionary[:MAX_ITEMS],
        "level": {"rms": round(max(lv["rms"] for lv in levels), 4), "peak": round(max(lv["peak"] for lv in levels), 4),
                  "clipping": round(max(lv["clipping"] for lv in levels), 4),
                  "advice": next((lv["advice"] for lv in reversed(levels) if lv["advice"] != "ok"), "ok")},
        "assistant": get_assistant_name(),
        "conditions": conditions,
        "tips": tips,
        "results": results,
    }
    people.save(profile)
    return profile["voice_training"]
