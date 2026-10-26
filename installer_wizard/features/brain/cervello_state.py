"""Stato permanente dell'applicazione Cervello, condiviso da tutti i dispositivi.

Contiene i server Ollama remoti inseriti dall'utente, il default globale scelto con
"Sincronizza Tutti i Moduli" e le sovrascritture per singolo modulo. Vive sul server
(non nel browser) cosi' ogni PC vede la stessa configurazione.
"""
import json
import threading
from pathlib import Path

from config import STATE_DIR

_LOCK = threading.Lock()
_MAX_SERVERS = 50
_MAX_TARGETS = 200
_MAX_BYTES = 512 * 1024


def _path() -> Path:
    return STATE_DIR / "brain" / "cervello.json"


def _clean(raw: object) -> dict:
    data = raw if isinstance(raw, dict) else {}
    servers = data.get("servers")
    targets = data.get("targets")
    default = data.get("globalDefault")
    return {
        "servers": [s for s in servers if isinstance(s, dict)][:_MAX_SERVERS] if isinstance(servers, list) else [],
        "targets": [t for t in targets if isinstance(t, dict)][:_MAX_TARGETS] if isinstance(targets, list) else [],
        "globalDefault": default if isinstance(default, dict) else None,
    }


def load() -> dict:
    with _LOCK:
        try:
            return _clean(json.loads(_path().read_text(encoding="utf-8")))
        except (OSError, ValueError):
            return _clean({})


def save(patch: dict) -> dict:
    """Aggiorna solo le chiavi presenti in `patch` e scrive il file in modo atomico."""
    with _LOCK:
        try:
            current = _clean(json.loads(_path().read_text(encoding="utf-8")))
        except (OSError, ValueError):
            current = _clean({})
        merged = _clean({**current, **{k: v for k, v in patch.items() if k in current}})
        payload = json.dumps(merged, ensure_ascii=False, separators=(",", ":"))
        if len(payload.encode("utf-8")) > _MAX_BYTES:
            raise ValueError("stato troppo grande")
        target = _path()
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".tmp")
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(target)
        return merged
