import re

_HOST = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,252}$")
SHARE = "condivisa"


def with_default_target(settings: dict, host: str) -> dict:
    if settings.get("NUXIVA_SCREENSHOT") != "1" or settings.get("NUXIVA_SCREENSHOT_TARGET"):
        return settings
    if not _HOST.match(host or ""):
        return settings
    return {**settings, "NUXIVA_SCREENSHOT_TARGET": f"smb://{host}/{SHARE}"}
