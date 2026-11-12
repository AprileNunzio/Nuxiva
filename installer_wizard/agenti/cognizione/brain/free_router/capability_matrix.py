from collections.abc import Mapping

POOLS = ("voice_fast", "agent_tools", "vision", "deep_code", "chat")


def supports(model: Mapping, pool: str, metrics: Mapping | None = None) -> bool:
    metrics = metrics or {}
    if pool == "voice_fast":
        return float(metrics.get("ttft_ms") or 0) > 0 and float(metrics.get("ttft_ms") or 0) < 300 and float(metrics.get("tokens_per_second") or 0) >= 60
    if pool == "agent_tools":
        return model.get("tools") is True and model.get("json") is True
    if pool == "vision":
        return model.get("vision") is True
    if pool == "deep_code":
        return int(model.get("context") or 0) >= 32000 and model.get("reasoning") is True
    if pool == "chat":
        return int(model.get("context") or 0) > 0
    return False


def candidates(models: list[dict], pool: str, metrics: Mapping[str, Mapping] | None = None) -> list[dict]:
    scores = metrics or {}
    eligible = [model for model in models if supports(model, pool, scores.get(model.get("id", "")))]
    eligible.sort(key=lambda model: (
        -float(scores.get(model["id"], {}).get("quota_pct") or 0),
        float(scores.get(model["id"], {}).get("ttft_ms") or 0),
        -float(scores.get(model["id"], {}).get("tokens_per_second") or 0),
        model["id"],
    ))
    return eligible
