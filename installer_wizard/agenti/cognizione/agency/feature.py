from config import env_get


def enabled() -> bool:
    return env_get("NUXIVA_AGENCY", "1") != "0"


def forge_enabled() -> bool:
    return env_get("NUXIVA_AGENCY_FORGE", "1") != "0"
