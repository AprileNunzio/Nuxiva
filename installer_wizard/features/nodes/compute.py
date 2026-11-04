from typing import Callable

MODEL_LIMIT = 64
NAME_LIMIT = 80


def _number(value, ceiling: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0
    return round(max(0.0, min(float(value), ceiling)), 2)


def _models(raw, text: Callable) -> list[dict]:
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw[:MODEL_LIMIT]:
        if not isinstance(item, dict):
            continue
        name = text(item.get("name"), NAME_LIMIT)
        if name:
            out.append({"name": name, "size_gb": _number(item.get("size_gb"), 4096.0)})
    return out


def clean(raw, text: Callable) -> dict:
    if not isinstance(raw, dict) or not isinstance(raw.get("ollama"), dict):
        return {}
    ollama = raw["ollama"]
    return {"ollama": {"available": bool(ollama.get("available")), "shared": bool(ollama.get("shared")),
                       "version": text(ollama.get("version"), 24), "models": _models(ollama.get("models"), text),
                       "running": _models(ollama.get("running"), text)}}


def ollama_ready(node: dict) -> bool:
    state = (node.get("compute") or {}).get("ollama") or {}
    return bool(state.get("available") and state.get("shared"))
