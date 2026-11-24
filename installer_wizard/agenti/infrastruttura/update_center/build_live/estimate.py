from __future__ import annotations

import json
import logging
import math
from typing import Any, Dict, List, Optional, Sequence

try:
    import nuxiva_native as _native
except ImportError:
    _native = None

log = logging.getLogger(__name__)
RUST = _native is not None and hasattr(_native, "update_build_eta")
ENGINE = "rust" if RUST else "python"
MAX_UNITS = 512
WINDOW = 48
MIN_UNITS = 3
WINDOW_WEIGHT = 0.6


def _round(value: float) -> float:
    return round(value * 10) / 10


def _clean(units: Sequence[float], elapsed: float) -> List[float]:
    out = sorted(float(t) for t in units if isinstance(t, (int, float)) and math.isfinite(t) and 0 <= t <= elapsed + 1)
    return out[-MAX_UNITS:]


def _window_rate(units: List[float]) -> Optional[float]:
    tail = units[-WINDOW:]
    if len(tail) < 3 or tail[-1] - tail[0] <= 0:
        return None
    return (len(tail) - 1) / (tail[-1] - tail[0])


def _variability(units: List[float]) -> float:
    tail = units[-WINDOW:]
    gaps = [b - a for a, b in zip(tail, tail[1:])]
    if len(gaps) < 2:
        return 1.0
    mean = sum(gaps) / len(gaps)
    if mean <= 0:
        return 1.0
    var = sum((g - mean) ** 2 for g in gaps) / len(gaps)
    return min(3.0, math.sqrt(var) / mean)


def _confidence(rel: float) -> str:
    return "high" if rel < 0.25 else "medium" if rel < 0.5 else "low"


def python_estimate(done: int, total: int, elapsed: float, units: Sequence[float]) -> Dict[str, Any]:
    elapsed = elapsed if isinstance(elapsed, (int, float)) and math.isfinite(elapsed) and elapsed > 0 else 0.0
    clean = _clean(units, elapsed)
    overall = done / elapsed if elapsed > 0 and done > 0 else None
    window = _window_rate(clean)
    if window is not None and overall is not None:
        rate: Optional[float] = WINDOW_WEIGHT * window + (1 - WINDOW_WEIGHT) * overall
    else:
        rate = window if window is not None else overall
    remaining = max(total - done, 0) if total > 0 else None
    out: Dict[str, Any] = {"rate_per_min": _round(rate * 60) if rate is not None else None, "remaining": remaining,
                           "eta": None, "eta_low": None, "eta_high": None, "confidence": None}
    if remaining is None or rate is None or done < MIN_UNITS or rate <= 0:
        return out
    base = remaining / rate
    since_last = max(elapsed - clean[-1], 0.0) if clean else 0.0
    eta = max(base - since_last, base * 0.1)
    rel = min(1.5, min(0.9, max(0.12, 1.6 / math.sqrt(done))) + 0.3 * _variability(clean))
    out.update(eta=_round(eta), eta_low=_round(max(eta * (1 - 0.6 * rel), 0.0)), eta_high=_round(eta * (1 + rel)),
               confidence=_confidence(rel))
    return out


def estimate(done: int, total: int, elapsed: float, units: Sequence[float]) -> Dict[str, Any]:
    if RUST:
        sample = json.dumps({"done": int(done), "total": int(total), "elapsed": float(elapsed),
                             "units": [float(t) for t in list(units)[-MAX_UNITS:]]})
        try:
            return json.loads(_native.update_build_eta(sample))
        except (ValueError, RuntimeError) as exc:
            log.warning("stima della compilazione nativa non riuscita, uso Python: %s", exc)
    return python_estimate(done, total, elapsed, units)
