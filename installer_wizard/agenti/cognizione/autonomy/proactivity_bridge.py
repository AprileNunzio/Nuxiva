import logging
import re
import time

from agenti.autonomy import proactivity
from agenti.autonomy import proactivity_schema as sc

log = logging.getLogger("nuxiva.autonomy.proactivity.bridge")
_state = {"installed": False, "days": {}}
_SAFE = re.compile(r"[^a-z0-9._:-]")


def short(entity: str) -> str:
    return _SAFE.sub("", entity.split(".", 1)[-1].lower())[:64]


def first_today(slug: str, now: float) -> bool:
    day = int(now // 86_400)
    if _state["days"].get(slug) == day:
        return False
    if len(_state["days"]) >= 256:
        _state["days"].clear()
    _state["days"][slug] = day
    return True


def translate(event: dict, now: float, present: list) -> list:
    name = event.get("name")
    data = event.get("data") or {}
    slug = str(data.get("slug") or "")
    if name == "person_arrived" and sc.person_ok(slug):
        out = [("presence", "home", slug, "", 1)]
        if first_today(slug, now):
            out.append(("schedule", "wake", slug, slug, 1))
        return out
    if name == "person_left" and sc.person_ok(slug):
        return [("presence", "home", slug, "", 0)]
    if name != "state_changed":
        return []
    entity = str(data.get("entity_id") or "")
    to = str(data.get("to") or "").lower()
    before = str(data.get("from") or "").lower()
    if entity.startswith("binary_sensor.") and "window" in entity and to in ("on", "off"):
        return [("home", "window_open", None, short(entity), 1 if to == "on" else 0)]
    if entity == "sun.sun" and to in ("below_horizon", "night") and before != to:
        return [("home", "dusk", p, "casa", 1) for p in present]
    if ("intrusion" in entity or entity.startswith("alarm_control_panel.")) and to in ("on", "triggered"):
        return [("security", "intrusion", None, short(entity), 1)]
    return []


def _on_event(event: dict) -> None:
    try:
        present, _guests = proactivity.audience()
        for domain, key, person, subject, value in translate(event, time.time(), present):
            proactivity.feed(domain, key, person, subject, value)
    except (ValueError, OSError, RuntimeError, KeyError) as exc:
        log.warning("Evento non tradotto in segnale di proattività: %s", exc)


def install() -> None:
    if _state["installed"]:
        return
    from agenti.automations.bus import bus
    bus.listen(_on_event)
    _state["installed"] = True
