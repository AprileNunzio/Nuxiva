import math

from agenti.rescue import policy as policy_rules
from agenti.rescue.signals import HALF_LIFE, HAZARDS, HAZARDS_OF, KINDS, MAX_FUTURE_S, MODALITY, RELIABILITY, expired

PRIOR_LOGIT = -3.0
GAIN = 1.6
SAME_KIND_DISCOUNT = 0.5
SAME_MODALITY_DISCOUNT = 0.85
P_FLOOR = 0.001
MAX_LOGIT = 9.0
ORDER = {k: i for i, k in enumerate(KINDS)}


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _logit(p: float) -> float:
    p = min(1.0 - P_FLOOR, max(P_FLOOR, p))
    return math.log(p / (1.0 - p))


def _decay(e: dict, now: float) -> float:
    age = max(0.0, now - e["at"])
    return math.exp(-age * math.log(2.0) / HALF_LIFE[e["kind"]])


def _reliability(policy: dict, kind: str) -> float:
    return policy_rules.reliability_of(policy, kind, RELIABILITY[kind])


def _strength(e: dict, policy: dict, now: float) -> float:
    effective = 0.5 + (e["probability"] - 0.5) * e["confidence"]
    signed = _logit(effective) * GAIN * _reliability(policy, e["kind"]) * _decay(e, now)
    return -signed if e["kind"] == "all_clear" else signed


def _collect(evidence: list[dict], policy: dict, now: float) -> dict:
    by_source: dict[tuple, list] = {}
    for e in evidence:
        if expired(e, now) or e["at"] > now + MAX_FUTURE_S:
            continue
        s = _strength(e, policy, now)
        c = e["confidence"] * _reliability(policy, e["kind"]) * _decay(e, now)
        slot = by_source.setdefault((ORDER[e["kind"]], e["source"]), [0.0, 0.0])
        if abs(s) > abs(slot[0]):
            slot[0] = s
        slot[1] = max(slot[1], c)
    groups: dict[str, dict] = {}
    for (order, _), (s, c) in sorted(by_source.items(), key=lambda item: (item[0][0], item[0][1].encode())):
        g = groups.setdefault(KINDS[order], {"weights": [], "certainty": 1.0})
        g["weights"].append(s)
        g["certainty"] *= 1.0 - min(1.0, max(0.0, c))
    for g in groups.values():
        g["weights"].sort(key=lambda w: -abs(w))
    return groups


def _kind_weight(group: dict) -> float:
    factor, total = 1.0, 0.0
    for w in group["weights"]:
        total += w * factor
        factor *= SAME_KIND_DISCOUNT
    return total


def _hazard_risk(hazard: str, groups: dict) -> dict | None:
    drivers = [{"kind": k, "weight": _kind_weight(groups[k]), "sources": len(groups[k]["weights"])}
               for k in KINDS if k in groups and hazard in HAZARDS_OF[k]]
    if not drivers:
        return None
    drivers.sort(key=lambda d: (-abs(d["weight"]), ORDER[d["kind"]]))
    seen: dict[str, float] = {}
    total, doubt = PRIOR_LOGIT, 1.0
    for d in drivers:
        factor = seen.setdefault(MODALITY[d["kind"]], 1.0)
        total += d["weight"] * factor
        seen[MODALITY[d["kind"]]] = factor * SAME_MODALITY_DISCOUNT
        doubt *= groups[d["kind"]]["certainty"]
    modalities = len({MODALITY[d["kind"]] for d in drivers if d["weight"] > 0.0})
    return {"hazard": hazard, "risk": sigmoid(min(MAX_LOGIT, max(-MAX_LOGIT, total))),
            "confidence": min(1.0, max(0.0, 1.0 - doubt)), "modalities": modalities, "drivers": drivers}


def assess(evidence: list[dict], policy: dict, now: float) -> dict:
    groups = _collect(evidence, policy, now)
    hazards = [h for h in (_hazard_risk(name, groups) for name in HAZARDS) if h is not None]
    return {"at": now, "hazards": hazards}


def risk(assessment: dict, hazard: str) -> float:
    for h in assessment["hazards"]:
        if h["hazard"] == hazard:
            return h["risk"]
    return sigmoid(PRIOR_LOGIT)


def peak(assessment: dict) -> float:
    return max((h["risk"] for h in assessment["hazards"]), default=0.0)
