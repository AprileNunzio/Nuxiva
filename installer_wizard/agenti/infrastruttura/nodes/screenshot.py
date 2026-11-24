import re

_HOST = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,252}$")
_USER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\\-]{0,63}$")
SHARE = "condivisa"
SHARE_USER = "nuxiva-share"
MAX_PASSWORD = 256


def enabled(settings: dict) -> bool:
    value = str(settings.get("NUXIVA_SCREENSHOT") or "").strip()
    if value in ("0", "1"):
        return value == "1"
    return str(settings.get("NUXIVA_SHARES") or "1").strip() != "0"


def with_default_target(settings: dict, host: str) -> dict:
    if not enabled(settings):
        return settings
    out = {**settings, "NUXIVA_SCREENSHOT": "1"}
    if out.get("NUXIVA_SCREENSHOT_TARGET") or not _HOST.match(host or ""):
        return out
    return {**out, "NUXIVA_SCREENSHOT_TARGET": f"smb://{host}/{SHARE}"}


def _clean_password(raw) -> str:
    text = str(raw or "")
    if not text or len(text) > MAX_PASSWORD or any(ord(c) < 32 or ord(c) == 127 for c in text):
        return ""
    return text


def credentials(settings: dict, host: str, env: dict) -> dict:
    target = str(settings.get("NUXIVA_SCREENSHOT_TARGET") or "")
    if not enabled(settings) or not target.startswith("smb://"):
        return {}
    if _HOST.match(host or "") and target.rstrip("/").lower() == f"smb://{host}/{SHARE}".lower():
        user, password = SHARE_USER, _clean_password(env.get("NUXIVA_SMB_PASSWORD"))
    else:
        user = str(settings.get("NUXIVA_SCREENSHOT_SMB_USER") or "").strip()
        password = _clean_password(env.get("NUXIVA_SCREENSHOT_SMB_PASSWORD"))
    if not password or not _USER.match(user):
        return {}
    return {"target": target.rstrip("/"), "user": user, "password": password}
