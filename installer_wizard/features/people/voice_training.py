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


def language(lang: str | None) -> str:
    return lang if lang in PLANS else "it"


def plan(lang: str | None, custom_name: str | None = None) -> list[dict]:
    name = custom_name or get_assistant_name()
    chosen = PLANS[language(lang)]
    out = []
    for kind in KINDS:
        for template in chosen[kind]:
            text = template.replace("Nuxiva", name).replace("nuxiva", name.lower())
            out.append({"kind": kind, "text": text})
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
    return {"kind": kind, "said": said, "heard": heard, "ok": ok, "variant": variant}


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
    profile["voice_training"] = {
        "trained_at": time.time(),
        "language": language(lang),
        "score": round(100 * sum(r["ok"] for r in results) / len(results)),
        "wake_variants": variants,
        "dictionary": dictionary[:MAX_ITEMS],
        "level": {"rms": round(max(lv["rms"] for lv in levels), 4), "peak": round(max(lv["peak"] for lv in levels), 4),
                  "clipping": round(max(lv["clipping"] for lv in levels), 4),
                  "advice": next((lv["advice"] for lv in reversed(levels) if lv["advice"] != "ok"), "ok")},
        "results": results,
    }
    people.save(profile)
    return profile["voice_training"]
