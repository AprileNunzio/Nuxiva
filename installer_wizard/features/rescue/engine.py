import json
import math

import native_core

from features.rescue import policy as policy_rules
from features.rescue.escalation import Escalation
from features.rescue.fusion import assess as py_assess
from features.rescue.signals import MAX_EVIDENCE, EvidenceError, evidence, validate

AREA = "rescue"


def _now(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise EvidenceError("rescue.evidence.time")
    return float(value)


def _tier(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 255:
        raise ValueError("rescue.tier")
    return value


class Rescue:
    def __init__(self, policy: str = "", prefer_native: bool = True) -> None:
        cls = native_core.symbol("RustRescue") if prefer_native else None
        self._native = cls(policy) if cls is not None else None
        self._py = None if self._native is not None else Escalation(policy_rules.parse(policy))
        if self._native is None and prefer_native:
            native_core.python_fallback(AREA)

    @property
    def native(self) -> bool:
        return self._native is not None

    def observe(self, kind: str, probability: float, confidence: float, source: str, at: float, now: float,
                room: str | None = None) -> None:
        now = _now(now)
        if self._native is not None:
            self._native.observe(kind, float(probability), float(confidence), source, float(at), now, room)
            return
        self._py.observe(evidence(kind, probability, confidence, source, at, room), now)

    def _call(self, name: str, *args) -> dict:
        if self._native is not None:
            return json.loads(getattr(self._native, name)(*args))
        return getattr(self._py, name)(*args)

    def update(self, now: float) -> dict:
        return self._call("update", _now(now))

    def person_ok(self, now: float) -> dict:
        return self._call("person_ok", _now(now))

    def need_help(self, now: float) -> dict:
        return self._call("need_help", _now(now))

    def acknowledge(self, tier: int, now: float) -> dict:
        return self._call("acknowledge", _tier(tier), _now(now))

    def dismiss(self, now: float) -> dict:
        return self._call("dismiss", _now(now))

    def timeline(self) -> list[dict]:
        if self._native is not None:
            return json.loads(self._native.timeline())
        return [dict(e) for e in self._py.timeline]

    def policy(self) -> dict:
        if self._native is not None:
            return json.loads(self._native.policy())
        return dict(self._py.policy)


def assess(items: list[dict], now: float, policy: str = "", prefer_native: bool = True) -> dict:
    now = _now(now)
    if len(items) > MAX_EVIDENCE:
        raise EvidenceError("rescue.evidence.too_many")
    fn = native_core.symbol("rescue_assess") if prefer_native else None
    if fn is not None:
        return json.loads(fn(json.dumps(items), now, policy))
    rules = policy_rules.parse(policy)
    for item in items:
        validate(item, now)
    return py_assess(items, rules, now)
