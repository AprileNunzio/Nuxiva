import json
import math

from agenti.rescue.signals import KINDS

SENSITIVITY = {"low": 1.2, "normal": 1.0, "high": 0.75}
MAX_TIERS = 5
MAX_ROUNDS = 5
DEFAULTS = {
    "sensitivity": "normal", "watch": 0.15, "check": 0.35, "alert": 0.7, "critical": 0.9,
    "check_in_s": 30.0, "alert_grace_s": 12.0, "family_ack_s": 120.0, "family_tiers": 2,
    "emergency_repeat_s": 180.0, "emergency_rounds": 3, "cooldown_s": 300.0, "reliability": {},
}


class PolicyError(ValueError):
    pass


def _within(value, lo: float, hi: float) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and lo <= value <= hi


def _int(value, lo: int, hi: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and lo <= value <= hi


def validate(p: dict) -> dict:
    if not (_within(p["watch"], 0.02, 0.6) and _within(p["check"], 0.05, 0.8) and _within(p["alert"], 0.1, 0.95)
            and _within(p["critical"], 0.2, 0.99) and p["watch"] < p["check"] < p["alert"] < p["critical"]):
        raise PolicyError("rescue.policy.thresholds")
    if not (_within(p["check_in_s"], 10.0, 180.0) and _within(p["alert_grace_s"], 3.0, 60.0)
            and p["alert_grace_s"] <= p["check_in_s"] and _within(p["family_ack_s"], 30.0, 900.0)
            and _within(p["emergency_repeat_s"], 60.0, 1800.0) and _within(p["cooldown_s"], 30.0, 3600.0)):
        raise PolicyError("rescue.policy.timing")
    if not (_int(p["family_tiers"], 1, MAX_TIERS) and _int(p["emergency_rounds"], 1, MAX_ROUNDS)):
        raise PolicyError("rescue.policy.tiers")
    if any(not _within(v, 0.05, 1.0) for v in p["reliability"].values()):
        raise PolicyError("rescue.policy.reliability")
    return p


def parse(raw: str = "") -> dict:
    if len(raw) > 16_384:
        raise PolicyError("rescue.policy.format")
    data = {}
    if raw.strip():
        try:
            data = json.loads(raw)
        except ValueError as exc:
            raise PolicyError("rescue.policy.format") from exc
    if not isinstance(data, dict) or set(data) - set(DEFAULTS) or data.get("sensitivity", "normal") not in SENSITIVITY:
        raise PolicyError("rescue.policy.format")
    reliability = data.get("reliability", {})
    if not isinstance(reliability, dict) or set(reliability) - set(KINDS):
        raise PolicyError("rescue.policy.format")
    merged = {**DEFAULTS, **data, "reliability": dict(reliability)}
    for key in ("watch", "check", "alert", "critical", "check_in_s", "alert_grace_s", "family_ack_s",
                "emergency_repeat_s", "cooldown_s"):
        if isinstance(merged[key], int) and not isinstance(merged[key], bool):
            merged[key] = float(merged[key])
    return validate(merged)


def reliability_of(p: dict, kind: str, default: float) -> float:
    return p["reliability"].get(kind, default)


def scaled(p: dict, key: str) -> float:
    return min(0.99, max(0.01, p[key] * SENSITIVITY[p["sensitivity"]]))
