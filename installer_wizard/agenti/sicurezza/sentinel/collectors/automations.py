import re

from agenti.sentinel import record

IDENT = re.compile(r"[^a-z0-9_.:-]+")


def _ident(raw) -> str:
    return (IDENT.sub("-", str(raw or "").lower()).strip("-") or "automation")[:96]


def on_event(event: dict) -> None:
    name = event.get("name")
    if name not in ("automation_started", "automation_finished") or not record.enabled():
        return
    data = event.get("data") or {}
    label = str(data.get("automation") or "")[:80]
    subject = record.automation(_ident(data.get("id") or label))
    if name == "automation_started":
        record.record("automation.started", subject, "sentinel.automation.started", {"automation": label},
                      "household", "automations")
        return
    failed = data.get("status") == "errore"
    record.record("automation.failed" if failed else "automation.finished", subject,
                  "sentinel.automation.failed" if failed else "sentinel.automation.finished",
                  {"automation": label}, "household", "automations")
