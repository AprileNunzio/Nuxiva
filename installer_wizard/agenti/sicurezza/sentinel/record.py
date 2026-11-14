import hashlib
import hmac
import logging
import threading
import time

from agenti.collaudo.taps import sentinel_event
from agenti.desktop.privacy import flag
from agenti.sentinel import vault
from agenti.sentinel.journal import SentinelUnavailable, journal, new_id

log = logging.getLogger("nuxiva.sentinel")
SENSITIVITY = frozenset({"public", "household", "personal", "sensitive"})
_warned = threading.Event()


def enabled() -> bool:
    return flag("NUXIVA_SENTINEL", True)


def option(key: str) -> bool:
    return enabled() and flag(key, True)


def pseudonym(slug: str) -> str:
    key = vault.secret("pseudonym")
    return hmac.new(key, b"nuxiva.sentinel.person:" + slug.strip().lower().encode(), hashlib.sha256).hexdigest()[:32]


def person(slug: str) -> dict:
    return {"type": "person", "id": pseudonym(slug)}


def guest(number: int) -> dict:
    return {"type": "guest", "id": int(number)}


NUXIVA = {"type": "nuxiva"}


def automation(ident: str) -> dict:
    return {"type": "automation", "id": ident}


def record(kind: str, subject: dict, key: str, params: dict | None = None, sensitivity: str = "household",
           source: str = "nuxiva", place: str | None = None, at: float | None = None) -> str | None:
    if not enabled():
        return None
    event = {"id": new_id(), "at_ms": int((at or time.time()) * 1000), "kind": kind, "subject": subject,
             "place": place, "narrative": {"key": key, "params": {k: str(v)[:120] for k, v in (params or {}).items()}},
             "sensitivity": sensitivity if sensitivity in SENSITIVITY else "household", "source": source, "links": []}
    try:
        stored = journal.append(event)
        sentinel_event(event)
        return stored
    except SentinelUnavailable:
        if not _warned.is_set():
            _warned.set()
            log.warning("Sentinella non attiva: modulo nativo assente, gli eventi non vengono registrati")
    except (ValueError, OSError) as exc:
        log.error("Evento Sentinella %s non registrato: %s", kind, exc)
    return None
