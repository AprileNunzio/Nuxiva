import logging
import os
import sys

from i18n.strings import t

try:
    import winreg
except ImportError:
    winreg = None

log = logging.getLogger("nuxiva.os_access")
ROOT = r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore"
SETTINGS = {"microphone": "ms-settings:privacy-microphone", "webcam": "ms-settings:privacy-webcam",
            "location": "ms-settings:privacy-location"}
KINDS = tuple(SETTINGS)
ALLOW, DENY, UNKNOWN = "allow", "deny", "unknown"


def _value(hive_name: str, kind: str) -> str:
    if winreg is None:
        return ""
    hive = getattr(winreg, hive_name)
    try:
        with winreg.OpenKey(hive, f"{ROOT}\\{kind}") as key:
            raw, _kind = winreg.QueryValueEx(key, "Value")
    except FileNotFoundError:
        return ""
    except OSError as exc:
        log.warning("Impossibile leggere il consenso %s: %s", kind, exc)
        return ""
    return str(raw).strip().lower()


def state(kind: str) -> str:
    if kind not in SETTINGS:
        raise KeyError(kind)
    values = (_value("HKEY_LOCAL_MACHINE", kind), _value("HKEY_CURRENT_USER", kind))
    if DENY in values:
        return DENY
    return ALLOW if ALLOW in values else UNKNOWN


def settings_uri(kind: str) -> str:
    return SETTINGS[kind]


def open_settings(kind: str) -> None:
    uri = settings_uri(kind)
    if sys.platform != "win32":
        raise OSError("Le impostazioni di Windows non sono disponibili su questo sistema")
    os.startfile(uri)


def blocked(kinds) -> list[str]:
    return [kind for kind in kinds if state(kind) == DENY]


def describe_all() -> list[str]:
    return [t(f"access.state.{state(kind)}", name=t(f"access.{kind}.name")) for kind in KINDS]
