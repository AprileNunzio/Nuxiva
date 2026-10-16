import json
from functools import lru_cache
from pathlib import Path

LANG_DIR = Path(__file__).resolve().parent / "language"
LANGS = ("it", "en", "es", "fr")
FALLBACK = "it"

SPECS = {
    "debian": {
        "icon": "🐧", "color": "#d70a53", "live": "debian",
        "skills": ["system_health", "service_diagnosis", "log_analysis", "security_updates"],
        "tools": ["debian_status", "debian_logs", "debian_service", "apt_upgradable", "run_command"],
        "keywords": ["debian", "linux", "server", "apt", "pacchett", "systemd", "servizi", "servizio", "log", "journal",
                     "disco", "memoria", "ram", "cpu", "carico", "kernel", "aggiorn", "porta", "rete", "dns"],
    },
    "football": {
        "icon": "⚽", "color": "#16c784", "live": "football",
        "skills": ["live_results", "standings", "team_analysis"],
        "tools": ["football_scores", "football_table", "football_team"],
        "keywords": ["calcio", "partit", "classific", "serie a", "serie b", "champions", "europa league", "gol",
                     "squadr", "campionat", "giornata", "marcator", "allenator", "risultat"],
    },
}


def lang_of(lang: str) -> str:
    code = str(lang or "").lower()[:2]
    return code if code in LANGS else FALLBACK


@lru_cache(maxsize=8)
def _texts(lang: str) -> dict:
    data = json.loads((LANG_DIR / f"{lang}.json").read_text(encoding="utf-8"))
    return data.get("templates") or {}


def text(template: str, lang: str) -> dict:
    texts = _texts(lang_of(lang))
    if template not in texts:
        texts = _texts(FALLBACK)
    return dict(texts.get(template) or {})


def catalog(lang: str) -> list[dict]:
    return [{"id": tid, **spec, **text(tid, lang)} for tid, spec in SPECS.items()]


def blueprint(template: str, lang: str, expert_id: str) -> dict:
    if template not in SPECS:
        raise KeyError(template)
    spec, words = SPECS[template], text(template, lang)
    return {"id": expert_id, "role": words["role"], "specialty": words["specialty"],
            "knowledge": list(words.get("knowledge") or []), "instructions": words.get("instructions", ""),
            "icon": spec["icon"], "color": spec["color"], "live": spec["live"], "tools": list(spec["tools"]),
            "skills": list(spec["skills"]),
            "template": template}


def keywords(template: str) -> list[str]:
    return list(SPECS.get(template, {}).get("keywords") or [])
