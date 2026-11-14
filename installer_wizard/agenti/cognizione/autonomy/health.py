import json
import logging

log = logging.getLogger("nuxiva.autonomy.health")
CLASSES = ("voice", "interactive", "background", "maintenance")
INITIATIVE_KEYS = ("surfaced", "accepted", "refused", "silent", "capped", "expired")


def _count(value) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def _queue() -> dict:
    try:
        from agenti.tasks import queue
        raw = json.loads(queue.get().stats())
        classes = {c: {"queued": _count(raw.get(c, {}).get("queued")), "running": _count(raw.get(c, {}).get("running"))} for c in CLASSES}
        return {"available": True, **classes, "journal_errors": _count(raw.get("journal_errors")), "dropped_events": _count(raw.get("dropped_events"))}
    except (ImportError, ValueError, RuntimeError, TypeError, AttributeError) as exc:
        log.warning("statistiche della coda non disponibili: %s", type(exc).__name__)
        return {"available": False}


def _initiative() -> dict:
    try:
        from agenti.autonomy import initiative
        raw = json.loads(initiative.get().stats())
        return {"available": True, **{k: _count(raw.get(k)) for k in INITIATIVE_KEYS}}
    except (ImportError, ValueError, RuntimeError, TypeError, AttributeError) as exc:
        log.warning("statistiche dell'iniziativa non disponibili: %s", type(exc).__name__)
        return {"available": False}


def _lessons() -> dict:
    try:
        from agenti.mind import reflect
        store = reflect.get()
        return {"available": True, **{s: len(json.loads(store.lessons(s))) for s in ("adopted", "candidate")}}
    except (ImportError, ValueError, RuntimeError, TypeError, AttributeError) as exc:
        log.warning("statistiche delle lezioni non disponibili: %s", type(exc).__name__)
        return {"available": False}


def _alerts(queue: dict, initiative: dict, lessons: dict) -> list[str]:
    alerts = []
    if not queue["available"]:
        alerts.append("queue_unavailable")
    elif queue["journal_errors"]:
        alerts.append("journal_errors")
    elif queue["dropped_events"]:
        alerts.append("events_dropped")
    if not initiative["available"]:
        alerts.append("initiative_unavailable")
    if not lessons["available"]:
        alerts.append("lessons_unavailable")
    return alerts


def snapshot() -> dict:
    queue, initiative, lessons = _queue(), _initiative(), _lessons()
    return {"queue": queue, "initiative": initiative, "lessons": lessons, "alerts": _alerts(queue, initiative, lessons)}
