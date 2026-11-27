import json
import re
from functools import lru_cache
from pathlib import Path

LANGUAGES = ("it", "en", "es", "fr")
NUMBER = re.compile(r"\d+")


@lru_cache(maxsize=4)
def words(language: str) -> dict:
    language = language if language in LANGUAGES else "it"
    return json.loads((Path(__file__).resolve().parent / "language" / f"{language}.json").read_text(encoding="utf-8"))


def render(fact: dict, language: str) -> str:
    template = words(language)["lines"].get(fact["line"], "")
    return template.format(**fact["params"]) if template else ""


def _join(items: list[str], language: str) -> str:
    if len(items) <= 1:
        return "".join(items)
    return f"{', '.join(items[:-1])} {words(language)['and']} {items[-1]}"


def verified_line(plan: dict, language: str) -> str:
    w = words(language)
    if not plan["verified"]:
        return ""
    if plan["verified_again"]:
        return w["verified_again"]
    return w["verified"].format(topics=_join([w["topics"].get(t, t) for t in plan["verified"]], language))


def fallback(plan: dict, facts: dict, language: str) -> str:
    w = words(language)
    parts = [w["greeting"][plan["daypart"]], w["openings"].get(plan["style"], "")]
    parts += [render(facts[c["key"]], language) for c in plan["facts"] if c["key"] in facts]
    parts.append(verified_line(plan, language))
    if not plan["facts"] and not plan["verified"]:
        parts.append(w["nothing"])
    return " ".join(p for p in parts if p).strip()


def unchanged(language: str, seed: int) -> str:
    options = words(language)["unchanged"]
    return options[seed % len(options)]


STYLE_HINTS = {
    "soft": "voce bassa e rassicurante, pochissime parole",
    "brief": "telegrafico, solo l'essenziale",
    "direct": "diretto e ordinato, prima la cosa più importante",
    "reassure": "rassicurante: prima dici che è tutto sotto controllo, poi i dettagli",
    "personal": "caloroso e personale, come un maggiordomo che conosce bene il suo signore",
    "curious": "apri con una curiosità o con la notizia più interessante",
    "playful": "brillante, con una sola battuta leggera e pertinente",
}
DAYPART_HINTS = {
    "night": "è notte fonda: sii discreto e brevissimo",
    "morning": "è mattina: energia pacata, utile per iniziare la giornata",
    "afternoon": "è pomeriggio",
    "evening": "è sera: tono rilassato",
    "late": "è tardi: tono basso e breve",
}


def prompt(plan: dict, facts: dict, persona: str, question: str) -> str:
    lines = [f"- [{facts[c['key']]['kind']}{', già detto prima' if c['repeat'] else ''}] {render(facts[c['key']], 'it')}"
             for c in plan["facts"] if c["key"] in facts]
    checked = verified_line(plan, "it")
    rules = [
        persona,
        "L'utente ti chiede come va. Rispondi su fatti reali, verificati adesso, elencati sotto: non inventarne altri, "
        "non aggiungere numeri, orari o nomi che non compaiono.",
        f"Stile: {STYLE_HINTS.get(plan['style'], 'garbato')}. Momento: {DAYPART_HINTS[plan['daypart']]}.",
        "Sii garbato e professionale. Rispondi nella stessa lingua della domanda.",
        "Massimo " + ("2 frasi." if plan["tone"] == "quiet" else "4 frasi."),
        "Puoi chiudere con una sola battuta leggera legata ai fatti." if plan["humor"] else "Nessuna battuta.",
        "Per i fatti già detti prima cambia angolazione: ricordali in breve o con quello che è cambiato.",
        "Se non ci sono fatti da segnalare dillo con naturalezza, senza elenchi.",
        "Fatti:", *(lines or ["- nessuna novità"]),
    ]
    if checked:
        rules.append(f"Controllo eseguito: {checked}")
    rules.append(f"Domanda: «{question[:300]}»")
    rules.append("Risposta:")
    return "\n".join(rules)


def grounded(reply: str, plan: dict, facts: dict, hour: int) -> bool:
    allowed = {str(hour), str(hour % 12 or 12), "24"}
    for c in plan["facts"]:
        for value in (facts.get(c["key"]) or {}).get("params", {}).values():
            allowed.update(NUMBER.findall(value))
    for t in plan["verified"]:
        allowed.update(NUMBER.findall(" ".join(str(v) for f in facts.values() if f["topic"] == t for v in f["params"].values())))
    return all(n in allowed for n in NUMBER.findall(reply))
