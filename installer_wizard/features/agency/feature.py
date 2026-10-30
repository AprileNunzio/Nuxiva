from config import env_get


def enabled() -> bool:
    return env_get("NUXIVA_AGENCY", "1") != "0"
