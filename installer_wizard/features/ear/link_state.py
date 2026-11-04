import json
import logging
import os
import time

log = logging.getLogger("nuxiva.ear")

LINK_FILE = os.environ.get("NUXIVA_EAR_LINK", "/var/lib/nuxiva/ear_link.json")
LINK = {"clients": 0, "last_audio": 0.0, "level": 0.0, "since": time.time(), "pages": []}


def save_link() -> None:
    try:
        tmp = LINK_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({**LINK, "at": time.time()}, f)
        os.replace(tmp, LINK_FILE)
    except OSError as exc:
        log.debug("Stato del collegamento non salvato: %s", exc)


def note_error(where: str, exc: Exception) -> None:
    text = f"{where}: {type(exc).__name__}: {exc}"[:240]
    if LINK.get("error") != text:
        log.exception("Errore nell'ascolto (%s)", where)
    LINK["error"], LINK["error_at"] = text, time.time()
