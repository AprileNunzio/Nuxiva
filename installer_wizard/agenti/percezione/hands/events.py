import logging
import threading
from collections import deque

log = logging.getLogger("nuxiva.hands")
RECENT_LIMIT = 40
TOPICS = {"gesture": "hands.gesture", "action": "hands.action"}
_recent: deque = deque(maxlen=RECENT_LIMIT)
_lock = threading.Lock()


def _publish(event: dict) -> None:
    try:
        from nuxiva_bus import BusError, nuxiva_bus
        nuxiva_bus.publish(TOPICS[event["type"]], event, origin="hands")
    except (ImportError, BusError) as exc:
        log.debug("Evento gesto non pubblicato sul bus: %s", exc)


def record(events: list) -> None:
    notable = [e for e in events if isinstance(e, dict) and e.get("type") in TOPICS]
    with _lock:
        _recent.extend(notable)
    for event in notable:
        _publish(event)


def recent() -> list:
    with _lock:
        return list(_recent)
