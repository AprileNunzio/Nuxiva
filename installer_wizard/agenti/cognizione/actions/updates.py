import re
import time

from state import store

from agenti.actions.common import sh
from agenti.update_center import system_runner

_EXPLICIT = re.compile(r"\b(installa|applica|conferm[oa]|procedi)\b", re.I)
_INSTALL = re.compile(r"\b(esegui|fai|aggiorna(ti|rti|re)?)\b", re.I)
_CHECK = re.compile(r"\b(controlla|verifica|ci sono|c'?[èe]|esistono|disponibil|stato|come sta andando)\b", re.I)
_CONFIRM = re.compile(r"\b(conferm[oa]|procedi)\b", re.I)
_STATUS = re.compile(r"\b(stato|come sta andando|a che punto)\b", re.I)
_RECENT = 3600


def _step_ids(plan: dict) -> list[str]:
    return [step["id"] for step in plan["steps"]]


def _items(info: dict, plan: dict) -> list[dict]:
    nuxiva_new = bool(info.get("available"))
    items = [
        {
            "label": "Nuxiva",
            "value": (
                f"{(info.get('local_rev') or '?')[:7]} → {(info.get('remote_rev') or '?')[:7]}"
                if nuxiva_new
                else f"aggiornato ({(info.get('local_rev') or '?')[:7]})"
            ),
            "status": "warn" if nuxiva_new else "ok",
        }
    ]
    parsed = plan.get("parsed", {})
    for change in parsed.get("upgrades", [])[:30]:
        items.append(
            {
                "label": change["name"],
                "value": "sicurezza" if change["security"] else "aggiornabile",
                "status": "bad" if change["security"] else "warn",
            }
        )
    for name in parsed.get("installs", [])[:5]:
        items.append({"label": name, "value": "nuova dipendenza", "status": "warn"})
    for name in parsed.get("removals", [])[:5]:
        items.append({"label": name, "value": "verrebbe rimosso", "status": "bad"})
    return items


def _describe(plan: dict, info: dict) -> str:
    nuxiva_new = bool(info.get("available"))
    parts = [
        f"Nuxiva ha un aggiornamento disponibile ({len(info.get('changelog') or [])} modifiche)"
        if nuxiva_new
        else "Nuxiva è alla versione più recente"
    ]
    if plan["packages"]:
        text = f"ci sono {plan['packages']} pacchetti di sistema da aggiornare"
        if plan["security"]:
            text += f", di cui {plan['security']} di sicurezza"
        parts.append(text)
    else:
        parts.append("il sistema operativo è aggiornato")
    return parts[0] + " e " + parts[1] + "."


def _status_line(run: dict) -> str:
    status = run.get("status")
    if status == "running":
        return "Un aggiornamento è in corso."
    if status == "restarting":
        return "L'ultimo aggiornamento è terminato e Nuxiva si sta riavviando."
    failed = [s for s in run.get("steps", []) if s["status"] == "failed"]
    if status == "failed" and failed:
        return f"L'ultimo aggiornamento non è riuscito al passo {failed[-1]['id']}."
    if status == "done":
        line = "L'ultimo aggiornamento è stato completato."
        if run.get("reboot_required"):
            line += " Serve un riavvio del computer per applicare gli aggiornamenti del sistema."
        return line
    return ""


async def _apply_nuxiva() -> bool:
    import updater

    return await updater.apply("richiesto a voce", force=True)


def _event(level: str, message: str) -> None:
    store.event(level, message, "actions")


async def updates_action(text: str) -> tuple[str, dict]:
    import updater

    wants_install = bool(_EXPLICIT.search(text)) or (bool(_INSTALL.search(text)) and not _CHECK.search(text))
    wants_status = bool(_STATUS.search(text))
    info = await updater.check(allow_bad=True)
    nuxiva_new = bool(info.get("available"))
    plan = await system_runner.build_plan(sh, nuxiva_new, str(info.get("remote_rev") or ""))
    run = system_runner.last_run()
    recent = bool(run) and time.time() - float(run.get("started") or 0) < _RECENT
    panel_items = _items(info, plan)
    if system_runner.running() or (wants_status and recent):
        speech = _status_line(run) or "Nessun aggiornamento recente."
    elif wants_install and plan["steps"]:
        needs_ok = plan["needs_confirmation"] and not (
            _CONFIRM.search(text) and system_runner.confirmation_valid(plan["id"])
        )
        if needs_ok:
            system_runner.request_confirmation(plan["id"])
            names = ", ".join(plan.get("parsed", {}).get("removals", [])[:4])
            speech = (
                f"Questo aggiornamento rimuoverebbe dei pacchetti ({names}). "
                "Se vuoi procedere dimmi «confermo gli aggiornamenti» entro dieci minuti."
            )
        else:
            started = system_runner.start(sh, plan, _apply_nuxiva, _event)
            speech = _launch_speech(plan) if started else "Un aggiornamento è già in corso."
    else:
        speech = _describe(plan, info)
        if plan["steps"]:
            speech += " Dimmi «installa gli aggiornamenti» e procedo con tutto, prima il sistema e poi Nuxiva."
        if plan["kept_back"]:
            speech += f" {plan['kept_back']} pacchetti restano indietro per dipendenze."
        if plan["stale"]:
            speech += " L'elenco dei pacchetti potrebbe non essere aggiornato: repository non raggiungibili."
        if recent and run.get("status") in ("done", "failed"):
            speech += " " + _status_line(run)
        if system_runner.reboot_required():
            speech += " Il sistema richiede un riavvio."
    return speech, {
        "mode": "focus",
        "title": "Aggiornamenti",
        "subtitle": "Nuxiva e sistema operativo",
        "panels": [{"type": "list", "title": f"Da aggiornare ({len(_step_ids(plan))} fasi)", "items": panel_items}],
    }


def _launch_speech(plan: dict) -> str:
    ids = _step_ids(plan)
    speech = "Avvio l'installazione"
    if "debian" in ids:
        speech += f": {plan['packages']} pacchetti di sistema"
    if "nuxiva" in ids:
        speech += (" e poi" if "debian" in ids else ":") + " la nuova versione di Nuxiva; mi riavvierò da sola e verificherò che tutto funzioni"
    speech += ". Ti avviso quando ho finito."
    if plan["reboot_likely"]:
        speech += " Potrebbe servire un riavvio del computer, non lo faccio senza il tuo permesso."
    return speech
