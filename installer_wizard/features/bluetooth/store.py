import json
import logging
import threading

from config import ETC_DIR, STATE_DIR
from cryptography.fernet import InvalidToken
from sealed import SealedFile

from features.bluetooth import schema
from features.bluetooth.adapter import valid_mac

log = logging.getLogger("nuxiva.bluetooth")
LEGACY_FILE = STATE_DIR / "bluetooth.json"
SEALED = SealedFile(STATE_DIR / "bluetooth.vault", ETC_DIR / "bluetooth.key")
GLOBALS = {"auto_switch": True, "auto_connect": True, "announce": True}
ORDERS = ("output_order", "input_order")
MAX_DEVICES = 64
_lock = threading.Lock()


def _default() -> dict:
    return {"devices": {}, "output_order": [], "input_order": [], **GLOBALS}


def _normalize(raw: object) -> dict:
    data = _default()
    if not isinstance(raw, dict):
        return data
    for key in GLOBALS:
        if isinstance(raw.get(key), bool):
            data[key] = raw[key]
    for key in ORDERS:
        values = raw.get(key) if isinstance(raw.get(key), list) else []
        data[key] = [m for m in dict.fromkeys(str(v).upper() for v in values) if schema_mac(m)][:MAX_DEVICES]
    devices = raw.get("devices") if isinstance(raw.get("devices"), dict) else {}
    for mac, entry in list(devices.items())[:MAX_DEVICES]:
        if schema_mac(str(mac).upper()) and isinstance(entry, dict):
            data["devices"][str(mac).upper()] = schema.migrate(entry)
    return data


def schema_mac(mac: str) -> bool:
    try:
        valid_mac(mac)
        return True
    except ValueError:
        return False


def _read() -> dict:
    if SEALED.data_path.exists():
        try:
            return _normalize(SEALED.load())
        except (InvalidToken, ValueError, OSError) as exc:
            log.error("Preferenze Bluetooth illeggibili, uso i valori predefiniti: %s", exc)
            return _default()
    if LEGACY_FILE.exists():
        try:
            data = _normalize(json.loads(LEGACY_FILE.read_text(encoding="utf-8")))
        except (ValueError, OSError) as exc:
            log.error("Preferenze Bluetooth legacy illeggibili: %s", exc)
            return _default()
        SEALED.save(data)
        LEGACY_FILE.unlink(missing_ok=True)
        return data
    return _default()


def load() -> dict:
    with _lock:
        return _read()


def _mutate(change) -> dict:
    with _lock:
        data = _read()
        change(data)
        SEALED.save(data)
        return data


def settings(data: dict, mac: str) -> dict:
    return schema.resolve(data["devices"].get(mac, {}))


def remember(mac: str, name: str, caps: list[str]) -> dict:
    mac = valid_mac(mac)

    def change(data: dict) -> None:
        entry = data["devices"].setdefault(mac, {})
        entry["name"] = schema.clean_text(name, 80)
        for cap, key in (("audio_out", "output_order"), ("audio_in", "input_order")):
            if cap in caps and mac not in data[key]:
                data[key].append(mac)
    return _mutate(change)


def forget(mac: str) -> dict:
    mac = valid_mac(mac)

    def change(data: dict) -> None:
        data["devices"].pop(mac, None)
        for key in ORDERS:
            data[key] = [m for m in data[key] if m != mac]
    return _mutate(change)


def update_device(mac: str, changes: object) -> dict:
    mac = valid_mac(mac)

    def change(data: dict) -> None:
        if mac not in data["devices"] and len(data["devices"]) >= MAX_DEVICES:
            raise ValueError("bluetooth_too_many_devices")
        data["devices"][mac] = schema.update(data["devices"].get(mac, {}), changes)
    return _mutate(change)


def update_globals(changes: object) -> dict:
    if not isinstance(changes, dict):
        raise ValueError("bluetooth_invalid_prefs")

    def change(data: dict) -> None:
        for key, value in changes.items():
            if key in GLOBALS:
                if not isinstance(value, bool):
                    raise ValueError(f"bluetooth_invalid_{key}")
                data[key] = value
            elif key in ORDERS:
                if not isinstance(value, list) or len(value) > MAX_DEVICES:
                    raise ValueError(f"bluetooth_invalid_{key}")
                data[key] = list(dict.fromkeys(valid_mac(m) for m in value))
            else:
                raise ValueError("bluetooth_unknown_pref")
    return _mutate(change)
