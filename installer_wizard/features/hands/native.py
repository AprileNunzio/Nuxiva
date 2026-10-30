import json

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None


def available() -> bool:
    return nuxiva_native is not None and hasattr(nuxiva_native, "RustGestureEngine")


def catalog() -> list[str]:
    return list(nuxiva_native.gesture_catalog()) if available() else []


def normalize(profile: dict) -> dict:
    return json.loads(nuxiva_native.gesture_validate_profile(json.dumps(profile)))


def defaults() -> dict:
    return normalize({}) if available() else {}


def engine(profile: dict):
    return nuxiva_native.RustGestureEngine(json.dumps(profile))

