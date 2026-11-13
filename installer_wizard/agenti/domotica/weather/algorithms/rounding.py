import math


def round_to(value: float, digits: int) -> float:
    scale = 10.0 ** digits
    return math.floor(value * scale + 0.5) / scale


def finite(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None
