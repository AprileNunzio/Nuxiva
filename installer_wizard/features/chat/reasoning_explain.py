import re

from features.brain.brains import CHAT_SLA_MS, brains
from features.chat.brain_chain import CONFIDENCE_BAD, CONFIDENCE_OK, CONFIDENCE_WEIGHT, CRITIC_WEIGHT, HARD_TIMEOUT_S, LEGACY_IDS, cortical_chain
from features.twin.simulator import CRITIC, RISK_TERMS
from server.core.reasoning.engines.auto_6_5 import engine as auto

MODE_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,48}$")


def _engine(mode: str):
    from server.core.reasoning.engines.scanner import engine_scanner
    return engine_scanner.get_engine(LEGACY_IDS.get(mode, mode))


def _limbic() -> dict:
    limbic = cortical_chain.limbic
    return {k: round(float(getattr(limbic, k)), 3) for k in ("valence", "arousal", "dopamine", "noradrenaline", "serotonin", "cortisol")}


def _groups(models: list[dict]) -> int:
    from itertools import groupby
    from features.cloud.catalog import is_cloud
    return sum(len(list(group)) if cloud else 1 for cloud, group in groupby((m["ref"] for m in models), key=is_cloud))


def _models(kind: str) -> list[dict]:
    cfg = brains.config()
    out = []
    for ref in brains.effective(kind, cfg, cfg["deep" if kind == "chat" else "chat"]):
        stats = brains.stats.get(ref, {})
        out.append({"ref": ref, "ok": int(stats.get("ok", 0)), "fail": int(stats.get("fail", 0)),
                    "avg_ms": round(float(stats["avg_ms"])) if stats else None})
    return out


def _card(engine, lang: str) -> dict:
    return {"id": engine.version.value, "name": engine.label(lang), "summary": engine.summary(lang), "strategy": engine.strategy.as_dict()}


def explain(mode: str, lang: str = "it") -> dict:
    mode = str(mode or "").strip().lower()
    if not MODE_RE.fullmatch(mode):
        raise ValueError("Motore non valido")
    engine = _engine(mode)
    if engine is None:
        raise LookupError(mode)
    kind = "chat" if engine.latency_sla_ms <= CHAT_SLA_MS else "deep"
    models = _models(kind)
    groups = _groups(models)
    strategy = engine.strategy
    rules = None
    if engine.version.value == auto.CognitiveEngineVersion.AUTO_6_5.value:
        rules = [{"when": when, **params, "engine": _card(_engine(version.value), lang)} for when, version, params in auto.RULES]
    return {
        **_card(engine, lang),
        "icon": engine.icon,
        "routing": {"kind": kind, "models": models, "candidates": groups},
        "launched": groups if strategy.pick == "sequential" else min(strategy.candidates, groups),
        "hard_timeout_s": HARD_TIMEOUT_S,
        "auto_rules": rules,
        "complexity_words": auto.COMPLEXITY_WORDS,
        "limbic": _limbic(),
        "scoring": {"confidence_ok": CONFIDENCE_OK, "confidence_bad": CONFIDENCE_BAD,
                    "confidence_weight": CONFIDENCE_WEIGHT, "critic_weight": CRITIC_WEIGHT},
        "critic": {**CRITIC, "risk_terms": list(RISK_TERMS)},
    }
