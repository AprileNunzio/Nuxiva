import json
import logging
import os

from agenti.firewall.defense import fallback

log = logging.getLogger("nuxiva.firewall")


def _native():
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "defense_assess", None)


RUST = _native()


def assess(payload: dict, native: bool = True) -> dict:
    if native and RUST is not None:
        return json.loads(RUST(json.dumps(payload, ensure_ascii=False, allow_nan=False)))
    return fallback.assess(payload)


def engine_name() -> str:
    return "rust" if RUST is not None else "python"
