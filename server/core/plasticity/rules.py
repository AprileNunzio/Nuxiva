import math

MIN_WEIGHT = 0.05
MAX_WEIGHT = 0.99
POTENTIATION_RATE = 0.10
DEPRESSION_RATE = 0.25
HALF_LIFE_DAYS = 30.0
PRUNE_BELOW = 0.10
PRUNE_IDLE_DAYS = 90.0


def _clamp(value: float) -> float:
    return min(MAX_WEIGHT, max(MIN_WEIGHT, value))


def potentiate(weight: float, rate: float = POTENTIATION_RATE) -> float:
    return _clamp(weight + rate * (1.0 - weight))


def depress(weight: float, rate: float = DEPRESSION_RATE) -> float:
    return _clamp(weight - rate * weight)


def decay(weight: float, idle_days: float, half_life: float = HALF_LIFE_DAYS) -> float:
    if idle_days <= 0:
        return weight
    return _clamp(weight * math.pow(0.5, idle_days / half_life))


def should_prune(weight: float, idle_days: float, protected: bool) -> bool:
    return not protected and weight <= PRUNE_BELOW and idle_days >= PRUNE_IDLE_DAYS

GRACE_DAYS = 7.0
MAX_ELAPSED_DAYS = 30.0
