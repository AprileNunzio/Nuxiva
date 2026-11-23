import json
import logging

from config import ETC_DIR, STATE_DIR
from sealed import SealedFile

log = logging.getLogger("nuxiva.network.store")
LEGACY = STATE_DIR / "devices.json"
VAULT = SealedFile(STATE_DIR / "devices.vault", ETC_DIR / "network_devices.key")


def load() -> dict:
    try:
        data = VAULT.load()
    except (OSError, ValueError) as exc:
        log.error("Registro dei dispositivi di rete illeggibile, riparto da quello in chiaro: %s", type(exc).__name__)
        data = {}
    if data:
        return data if isinstance(data, dict) else {}
    try:
        legacy = json.loads(LEGACY.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        log.error("Vecchio registro dei dispositivi illeggibile: %s", type(exc).__name__)
        return {}
    return legacy if isinstance(legacy, dict) else {}


def save(devices: dict) -> None:
    VAULT.save(devices)
    LEGACY.unlink(missing_ok=True)
