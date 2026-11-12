import json
from functools import lru_cache
from pathlib import Path

LANG_DIR = Path(__file__).resolve().parent / "language"
LANGS = ("it", "en", "es", "fr")
FALLBACK = "it"

CATALOG_FILE = Path(__file__).resolve().parent / "catalog.json"
DEFAULT_SKILLS: list[str] = []
DEFAULT_LIVE = "activity"

BUILTIN = {
    "debian": {
        "icon": "🐧", "color": "#d70a53", "live": "debian",
        "skills": ["system_health", "service_diagnosis", "log_analysis", "security_updates", "package_management",
                   "service_control", "power_management", "remote_ssh", "system_administration"],
        "tools": ["debian_status", "debian_logs", "debian_service", "apt_upgradable", "run_command", "debian_shell",
                  "debian_processes", "debian_network", "apt_install", "apt_remove", "apt_search", "apt_maintain",
                  "service_control", "power_control", "ssh_exec", "ssh_public_key", "system_file_read", "system_file_write",
                  "process_kill"],
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


def _catalog() -> dict:
    rows = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    return {r["id"]: {"icon": r["icon"], "color": r["color"], "live": DEFAULT_LIVE, "skills": DEFAULT_SKILLS, "group": r["group"],
                      "tools": r["tools"], "keywords": r["keywords"]} for r in rows}


SPECS = {**BUILTIN, **_catalog()}


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


@lru_cache(maxsize=8)
def _groups(lang: str) -> dict:
    return json.loads((LANG_DIR / f"{lang}.json").read_text(encoding="utf-8")).get("groups") or {}


def group_rules(group: str, lang: str) -> str:
    rules = _groups(lang_of(lang))
    return str(rules.get(group) or _groups(FALLBACK).get(group) or "")


def catalog(lang: str) -> list[dict]:
    return [{"id": tid, **spec, **text(tid, lang)} for tid, spec in SPECS.items()]


def ids() -> list[str]:
    return list(SPECS)


def blueprint(template: str, lang: str, expert_id: str) -> dict:
    if template not in SPECS:
        raise KeyError(template)
    spec, words = SPECS[template], text(template, lang)
    return {"id": expert_id, "role": words["role"], "specialty": words["specialty"],
            "knowledge": list(words.get("knowledge") or []),
            "instructions": words.get("instructions") or group_rules(spec.get("group", ""), lang),
            "icon": spec["icon"], "color": spec["color"], "live": spec["live"], "tools": list(spec["tools"]),
            "skills": list(spec["skills"]), "template": template}


def keywords(template: str) -> list[str]:
    return list(SPECS.get(template, {}).get("keywords") or [])


LEGACY_INSTRUCTIONS = frozenset({
    "Prima di proporre modifiche controlla sempre lo stato reale con i tuoi strumenti. Spiega cosa hai trovato e proponi comandi precisi; non eseguire nulla di distruttivo.",
    "Always check the real state with your tools before proposing changes. Explain what you found and propose precise commands; never run anything destructive.",
    "Vérifiez toujours l'état réel avec vos outils avant de proposer des changements. Expliquez ce que vous avez trouvé et proposez des commandes précises ; n'exécutez rien de destructif.",
    "Comprueba siempre el estado real con tus herramientas antes de proponer cambios. Explica lo que encontraste y propón comandos precisos; no ejecutes nada destructivo.",
})


def upgrade(row: dict) -> dict:
    spec = SPECS.get(str(row.get("template") or ""))
    if not spec:
        return row
    skills = list(dict.fromkeys([*(row.get("skills") or []), *spec["skills"]]))[:12]
    tools = list(dict.fromkeys([*(row.get("tools") or []), *spec["tools"]]))[:24]
    fresh = {**row, "skills": skills, "tools": tools}
    if row.get("instructions") in LEGACY_INSTRUCTIONS:
        fresh["instructions"] = text(row["template"], lang_of(row.get("lang") or FALLBACK)).get("instructions") or row["instructions"]
    return fresh
