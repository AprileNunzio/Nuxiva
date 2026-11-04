import re
from typing import Optional

_PATTERN = re.compile(r"^\s*([+-]?\d+(?:[.,]\d+)?)\s*([a-zA-Zµμ\u03a9\u03c9]*)")
_PREFIXES = {
    "p": 1e-12,
    "n": 1e-9,
    "u": 1e-6,
    "µ": 1e-6,
    "μ": 1e-6,
    "m": 1e-3,
    "k": 1e3,
    "meg": 1e6,
    "g": 1e9,
    "t": 1e12,
}
_UNITS = ("ohm", "ω", "hz", "f", "h", "v", "a", "w", "r")


def _strip_unit(suffix: str) -> str:
    lowered = suffix.lower()
    for unit in _UNITS:
        if lowered == unit:
            return ""
        if lowered.endswith(unit):
            return suffix[: -len(unit)]
    return suffix


def parse_value(raw: str) -> Optional[float]:
    match = _PATTERN.match(raw or "")
    if not match:
        return None
    number = float(match.group(1).replace(",", "."))
    prefix = _strip_unit(match.group(2))
    if not prefix:
        return number
    if prefix == "M":
        return number * 1e6
    multiplier = _PREFIXES.get(prefix.lower())
    return number * multiplier if multiplier is not None else None
