import threading
from collections import Counter, deque
from typing import Any

from server.core.hippocampus_router.contracts import RouteOutcome

RECENT_LIMIT = 50


class ArbiterTelemetry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._verdicts: Counter[str] = Counter()
        self._reasons: Counter[str] = Counter()
        self._total_latency_ms = 0.0
        self._max_latency_ms = 0.0
        self._executed = 0
        self._recent: deque[dict[str, Any]] = deque(maxlen=RECENT_LIMIT)

    def record(self, outcome: RouteOutcome) -> None:
        with self._lock:
            self._verdicts[outcome.verdict.value] += 1
            if outcome.reason:
                self._reasons[outcome.reason] += 1
            if outcome.degraded:
                self._reasons[outcome.degraded] += 1
            self._total_latency_ms += outcome.latency_ms
            self._max_latency_ms = max(self._max_latency_ms, outcome.latency_ms)
            self._executed += int(outcome.executed)
            self._recent.append(outcome.as_public_dict())

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            total = sum(self._verdicts.values())
            return {
                "total": total,
                "executed": self._executed,
                "verdicts": dict(self._verdicts),
                "reasons": dict(self._reasons),
                "latency_ms": {
                    "average": round(self._total_latency_ms / total, 3) if total else 0.0,
                    "maximum": round(self._max_latency_ms, 3),
                },
                "recent": list(self._recent),
            }
