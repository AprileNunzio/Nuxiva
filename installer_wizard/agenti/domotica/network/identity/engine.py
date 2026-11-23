import json
import logging

import native_core
from agenti.network.identity import fallback

log = logging.getLogger("nuxiva.network.identity")
FIELDS = ("key", "mac", "ip", "hostname")


def _known(devices: dict) -> list[dict]:
    return [{f: (str(d.get(f)) if d.get(f) is not None else None) for f in FIELDS} | {"key": str(key)}
            for key, d in devices.items() if isinstance(d, dict)]


def resolve(devices: dict, seen: dict) -> dict | None:
    known = _known(devices)
    probe = {"mac": seen.get("mac"), "ip": seen.get("ip"), "hostname": seen.get("hostname"), "own": bool(seen.get("own"))}
    native = native_core.symbol("device_resolve")
    if native is not None:
        try:
            return json.loads(native(json.dumps({"known": known, "seen": probe})))
        except ValueError as exc:
            log.warning("riconoscimento nativo non riuscito (%s), uso Python", type(exc).__name__)
    else:
        native_core.python_fallback("network.identity")
    return fallback.resolve(known, probe)
