import json
import re
import unicodedata
from functools import lru_cache

from features.experts.templates import FALLBACK, LANG_DIR, lang_of

SKILL_RE = re.compile(r"^[a-z][a-z0-9_]{2,40}$")

SKILLS: dict[str, dict] = {
    "system_health": {"tools": ["debian_status"], "keywords": ["stato", "salute", "come sta", "memoria", "ram", "disco", "spazio", "carico", "cpu", "temperatura", "uptime"]},
    "service_diagnosis": {"tools": ["debian_service", "debian_logs", "debian_status"], "keywords": ["servizio", "servizi", "systemd", "non parte", "fallit", "crash", "riavvi", "errore"]},
    "log_analysis": {"tools": ["debian_logs"], "keywords": ["log", "journal", "registro", "errori", "warning", "avvisi"]},
    "security_updates": {"tools": ["apt_upgradable", "run_command"], "keywords": ["aggiorn", "apt", "pacchett", "sicurezza", "upgrade", "update", "patch"]},
    "package_management": {"tools": ["apt_install", "apt_remove", "apt_search", "apt_maintain"], "keywords": ["install", "disinstall", "rimuov", "pacchett", "apt", "programma", "applicazion", "cerca"]},
    "service_control": {"tools": ["service_control", "debian_service", "debian_logs"], "keywords": ["avvia", "ferma", "riavvia il servizio", "servizio", "abilita", "disabilita", "systemctl", "demone"]},
    "power_management": {"tools": ["power_control", "debian_status"], "keywords": ["riavvia", "spegni", "spegnimento", "reboot", "poweroff", "sospendi", "shutdown", "annulla"]},
    "remote_ssh": {"tools": ["ssh_exec", "ssh_public_key"], "keywords": ["ssh", "remoto", "altro computer", "connettiti", "collegati", "macchina", "server remoto"]},
    "system_administration": {"tools": ["debian_shell", "system_file_read", "system_file_write", "debian_processes", "process_kill", "debian_network"], "keywords": ["comando", "terminale", "shell", "file", "configur", "processo", "uccidi", "kill", "porta", "rete", "cron", "utente", "permessi", "docker"]},
    "live_results": {"tools": ["football_scores"], "keywords": ["risultat", "partit", "oggi", "stasera", "diretta", "live", "gol", "segnato", "finita"]},
    "standings": {"tools": ["football_table"], "keywords": ["classific", "punti", "prima", "ultima", "retrocession", "zona champions"]},
    "team_analysis": {"tools": ["football_team", "football_scores"], "keywords": ["squadra", "prossima", "calendario", "ultime", "forma", "contro"]},
}


def _flat(text: str) -> str:
    return unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower()


@lru_cache(maxsize=8)
def _texts(lang: str) -> dict:
    return json.loads((LANG_DIR / f"{lang}.json").read_text(encoding="utf-8")).get("skills") or {}


def text(skill_id: str, lang: str) -> dict:
    texts = _texts(lang_of(lang))
    return dict(texts.get(skill_id) or _texts(FALLBACK).get(skill_id) or {})


def exists(skill_id: str) -> bool:
    return skill_id in SKILLS


def tools_of(skill_id: str) -> list[str]:
    return list(SKILLS.get(skill_id, {}).get("tools") or [])


def card(skill_id: str, lang: str) -> dict:
    words = text(skill_id, lang)
    return {"id": skill_id, "name": words.get("name", skill_id), "purpose": words.get("purpose", ""),
            "procedure": list(words.get("procedure") or []), "rules": list(words.get("rules") or []), "tools": tools_of(skill_id)}


def catalog(lang: str) -> list[dict]:
    return [card(sid, lang) for sid in SKILLS]


def suggest(skill_ids: list[str], question: str) -> str | None:
    body = _flat(question)
    scored = sorted(((sum(1 for k in SKILLS[s]["keywords"] if k in body), i, s) for i, s in enumerate(skill_ids) if s in SKILLS),
                    key=lambda r: (-r[0], r[1]))
    return scored[0][2] if scored and scored[0][0] > 0 else None


def briefing(skill_id: str, lang: str) -> str:
    c = card(skill_id, lang)
    steps = "\n".join(f"{i + 1}. {p}" for i, p in enumerate(c["procedure"]))
    rules = "\n".join(f"- {r}" for r in c["rules"])
    return f"Competenza attiva: {c['name']} — {c['purpose']}\nProcedura:\n{steps}\nVincoli:\n{rules}"
