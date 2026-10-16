import logging
import re

from features.brain.brains import CHAT_SLA_MS, brains
from features.twin.simulator import CRITIC, RISK_TERMS
from features.chat.brain_chain import (
    AUTO_COMPLEX, AUTO_EMPATHY_VALENCE, AUTO_FAST_COMPLEXITY, AUTO_FAST_NORADRENALINE, COMPLEXITY_WORDS, CONFIDENCE_BAD, CONFIDENCE_OK, CONFIDENCE_WEIGHT, CRITIC_WEIGHT, PRUNE_FACTOR,
    REASONING_PROFILES, cortical_chain,
)

log = logging.getLogger("nuxiva.reasoning")
MODE_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,48}$")
AUTO = "nuxiva-6.5-auto"


def _engine(mode: str):
    from server.core.reasoning.engines.scanner import engine_scanner
    engine_scanner.scan()
    return engine_scanner.get_engine(mode)


def _profile(mode: str, sla: int) -> tuple[dict, str]:
    if mode in REASONING_PROFILES:
        return dict(REASONING_PROFILES[mode]), "table"
    branches = 16 if sla > 600 else (8 if sla > 200 else (4 if sla > 50 else 2))
    depth = 4 if sla > 600 else (3 if sla > 200 else 1)
    return {"parallel_branches": branches, "mcts_depth": depth, "ignition_threshold": 0.85,
            "timeout_s": max(0.5, sla / 1000.0 * 2.0), "use_limbic": True, "use_twin_critic": sla > 100}, "sla"


def _limbic() -> dict:
    l = cortical_chain.limbic
    return {k: round(float(getattr(l, k)), 3) for k in
            ("valence", "arousal", "dopamine", "noradrenaline", "serotonin", "cortisol")}


def _budget(limbic: dict, branches: int) -> dict:
    if limbic["cortisol"] > 0.8:
        return {"rule": "stress", "factor": 0.25, "result": max(1, branches // 4)}
    factor = 0.5 + limbic["dopamine"] * 0.5 + limbic["serotonin"] * 0.2
    return {"rule": "explore", "factor": round(factor, 3), "result": max(1, min(branches, int(round(branches * factor))))}


def _candidates(models: list[dict]) -> int:
    from itertools import groupby
    from features.cloud.catalog import is_cloud
    count = 0
    for cloud, group in groupby((m["ref"] for m in models), key=is_cloud):
        count += len(list(group)) if cloud else 1
    return count


def _models(kind: str) -> list[dict]:
    cfg = brains.config()
    out = []
    for ref in brains.effective(kind, cfg, cfg["deep" if kind == "chat" else "chat"]):
        stats = brains.stats.get(ref, {})
        out.append({"ref": ref, "ok": int(stats.get("ok", 0)), "fail": int(stats.get("fail", 0)),
                    "avg_ms": round(float(stats["avg_ms"])) if stats else None})
    return out


def explain(mode: str) -> dict:
    mode = str(mode or "").strip().lower()
    if not MODE_RE.fullmatch(mode):
        raise ValueError("Motore non valido")
    engine = _engine(mode)
    if engine is None:
        raise LookupError(mode)
    version = getattr(engine.version, "value", str(engine.version))
    sla = int(engine.latency_sla_ms)
    kind = "chat" if sla <= CHAT_SLA_MS else "deep"
    profile, source = _profile(version, sla)
    limbic = _limbic()
    models = _models(kind)
    auto_rules = None
    if version == AUTO:
        source = "auto"
        auto_rules = [
            {"when": "fast", "noradrenaline_above": AUTO_FAST_NORADRENALINE, "complexity_below": AUTO_FAST_COMPLEXITY,
             "profile": "nuxiva-5.0-fast"},
            {"when": "empathetic", "abs_valence_above": AUTO_EMPATHY_VALENCE, "profile": "nuxiva-5.0-empathetic"},
            {"when": "complex", "complexity_above": AUTO_COMPLEX, "profile": "nuxiva-6.5-ultra"},
            {"when": "default", "profile": "nuxiva-6.0-pro"},
        ]
        for rule in auto_rules:
            rule["params"] = dict(REASONING_PROFILES[rule["profile"]])
    return {
        "id": version, "name": engine.name, "icon": getattr(engine, "icon", ""), "sla_ms": sla,
        "vram_mb": int(engine.vram_mb), "label": engine.architecture,
        "routing": {"kind": kind, "threshold_ms": CHAT_SLA_MS, "models": models, "candidates": _candidates(models)},
        "profile": {**profile, "source": source},
        "auto_rules": auto_rules,
        "complexity_words": int(COMPLEXITY_WORDS),
        "limbic": limbic,
        "budget": _budget(limbic, int(profile["parallel_branches"])),
        "scoring": {"confidence_ok": CONFIDENCE_OK, "confidence_bad": CONFIDENCE_BAD,
                    "confidence_weight": CONFIDENCE_WEIGHT, "critic_weight": CRITIC_WEIGHT,
                    "prune_factor": PRUNE_FACTOR,
                    "prune_below": round(float(profile["ignition_threshold"]) * PRUNE_FACTOR, 3)},
        "critic": {**CRITIC, "risk_terms": list(RISK_TERMS)},
    }
