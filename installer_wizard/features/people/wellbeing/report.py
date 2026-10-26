import time
from collections import Counter

from features.people import people
from features.people.wellbeing import store
from features.people.wellbeing.scoring import AREAS

DISCLAIMER = {
    "it": "Questo documento NON è una diagnosi né una cartella clinica. Raccoglie osservazioni di un assistente di benessere basate su ciò che la persona ha riferito e su stime automatiche del volto (non cliniche), pensato per essere discusso con un professionista della salute.",
    "en": "This document is NOT a diagnosis or a medical record. It gathers observations from a wellbeing assistant based on what the person reported and on automatic, non-clinical facial estimates, meant to be discussed with a health professional.",
    "fr": "Ce document n'est PAS un diagnostic ni un dossier médical. Il rassemble les observations d'un assistant de bien-être fondées sur ce que la personne a rapporté et sur des estimations faciales automatiques non cliniques, destinées à être discutées avec un professionnel de santé.",
    "es": "Este documento NO es un diagnóstico ni una historia clínica. Reúne observaciones de un asistente de bienestar basadas en lo que la persona refirió y en estimaciones faciales automáticas no clínicas, para comentarlas con un profesional sanitario.",
}
LABELS = {
    "it": ("Persona", "Percorso", "Sedute", "Andamento giornaliero", "Aree emotive", "Segnali di sicurezza", "Sedute", "Temi", "Riferito dalla persona", "Da approfondire", "Trascrizione", "Umore (0-10)", "Prima", "Dopo", "Nessuna"),
    "en": ("Person", "Path", "Sessions", "Daily trend", "Emotional areas", "Safety signals", "Sessions", "Themes", "Reported by the person", "To discuss", "Transcript", "Mood (0-10)", "Before", "After", "None"),
    "fr": ("Personne", "Parcours", "Séances", "Évolution quotidienne", "Zones émotionnelles", "Signaux de sécurité", "Séances", "Thèmes", "Rapporté par la personne", "À approfondir", "Transcription", "Humeur (0-10)", "Avant", "Après", "Aucun"),
    "es": ("Persona", "Recorrido", "Sesiones", "Evolución diaria", "Áreas emocionales", "Señales de seguridad", "Sesiones", "Temas", "Referido por la persona", "A profundizar", "Transcripción", "Ánimo (0-10)", "Antes", "Después", "Ninguna"),
}


def _day(at: float) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(at))


def daily(rows: list[dict]) -> list[dict]:
    days: dict[str, list[dict]] = {}
    for row in rows:
        days.setdefault(_day(row["at"]), []).append(row)
    out = []
    for day, items in sorted(days.items()):
        out.append({"day": day, "samples": len(items), "arousal": round(sum(r["arousal"] for r in items) / len(items), 1),
                    "areas": {a: sum(1 for r in items if r["area"] == a) for a in AREAS}})
    return out


def observations(rows: list[dict]) -> list[str]:
    trend = daily(rows)
    notes = []
    if len([d for d in trend if d["arousal"] >= 66]) >= 3:
        notes.append("high_tension_days")
    if len([d for d in trend if d["areas"]["exhaustion"] > d["samples"] / 2]) >= 3:
        notes.append("low_energy_days")
    return notes


def build(slug: str, lang: str = "it", transcripts: bool = False, now: float | None = None) -> dict:
    now = now or time.time()
    code = lang if lang in DISCLAIMER else "en"
    rows = store.readings(slug, now - 90 * 86400)
    sessions = []
    for s in reversed(store.sessions(slug)):
        item = {"id": s["id"], "date": _day(s["started"]), "stage": s["stage"], "minutes": round(((s["ended"] or s["started"]) - s["started"]) / 60),
                "mood_before": s["mood_before"], "mood_after": s["mood_after"], "risk_flags": s["risk"], "completed": bool(s["ended"]),
                "digest": store.summary(s["id"])}
        if transcripts:
            item["transcript"] = store.turns(s["id"])
        sessions.append(item)
    plan = store.plan(slug)
    profile = people.load(slug) or {}
    return {"generated": now, "language": code, "disclaimer": DISCLAIMER[code], "person": profile.get("name", slug),
            "plan": {"stage": plan["stage"], "next_at": plan["next_at"], "concluded": bool(plan["concluded"])},
            "sessions": sessions, "daily": daily(rows), "areas": dict(Counter(r["area"] for r in rows)),
            "observations": observations(rows), "safety": [{"date": s["date"], "flags": s["risk_flags"]} for s in sessions if s["risk_flags"]]}


def markdown(data: dict) -> str:
    L = LABELS.get(data["language"], LABELS["en"])
    lines = [f"# {L[2]}: {data['person']}", "", f"> {data['disclaimer']}", "", f"**{L[1]}**: {data['plan']['stage']}", ""]
    lines += [f"## {L[3]}", ""] + [f"- {d['day']}: {d['arousal']}/100 ({d['samples']})" for d in data["daily"]] + [""]
    lines += [f"## {L[4]}", ""] + [f"- {k}: {v}" for k, v in data["areas"].items()] + [""]
    lines += [f"## {L[5]}", ""] + ([f"- {s['date']}: {s['flags']}" for s in data["safety"]] or [f"- {L[14]}"]) + [""]
    lines += [f"## {L[6]}", ""]
    for s in data["sessions"]:
        digest = s["digest"] or {}
        lines += [f"### {s['date']} · {s['stage']} · {s['minutes']} min", "", f"{L[11]}: {L[12]} {s['mood_before']} / {L[13]} {s['mood_after']}", ""]
        if digest.get("summary"):
            lines += [digest["summary"], ""]
        for title, key in ((L[7], "themes"), (L[8], "reported"), (L[9], "for_professional")):
            if digest.get(key):
                lines += [f"**{title}**: " + "; ".join(digest[key]), ""]
        if s.get("transcript"):
            lines += [f"**{L[10]}**", ""] + [f"- {t['role']}: {t['text']}" for t in s["transcript"]] + [""]
    return "\n".join(lines)
