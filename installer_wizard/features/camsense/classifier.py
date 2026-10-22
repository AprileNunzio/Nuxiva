from dataclasses import dataclass

import numpy as np

MIN_SIMILARITY = 0.8
MIN_MARGIN = 0.03
NEIGHBOURS = 2


@dataclass(frozen=True)
class Verdict:
    label: str
    confidence: float
    margin: float
    reason: str

    def to_dict(self) -> dict:
        return {"label": self.label, "confidence": round(self.confidence, 3), "margin": round(self.margin, 3), "reason": self.reason}


def _score(samples: list[list[float]], probe: np.ndarray) -> float:
    sims = np.sort(np.array(samples, dtype=np.float64) @ probe)[::-1]
    return float(sims[:NEIGHBOURS].mean())


def classify(samples: dict[str, list[list[float]]], probe: list[float]) -> Verdict:
    usable = {label: rows for label, rows in samples.items() if rows}
    if len(usable) < 2:
        return Verdict("", 0.0, 0.0, "needs_two_states")
    target = np.array(probe, dtype=np.float64)
    ranked = sorted(((_score(rows, target), label) for label, rows in usable.items()), reverse=True)
    best, second = ranked[0], ranked[1]
    margin = best[0] - second[0]
    if best[0] < MIN_SIMILARITY:
        return Verdict("", best[0], margin, "unlike_any_state")
    if margin < MIN_MARGIN:
        return Verdict("", best[0], margin, "ambiguous")
    return Verdict(best[1], best[0], margin, "ok")
