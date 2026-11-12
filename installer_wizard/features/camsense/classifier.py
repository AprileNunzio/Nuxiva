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


TOO_SIMILAR = 0.985
MIN_EXAMPLES = 2


def _centroid(rows: list[list[float]]) -> np.ndarray:
    mean = np.array(rows, dtype=np.float64).mean(axis=0)
    norm = float(np.linalg.norm(mean))
    return mean / norm if norm > 1e-9 else mean


def quality(samples: dict[str, list[list[float]]]) -> dict:
    usable = {label: rows for label, rows in samples.items() if rows}
    if len(usable) < 2:
        return {"ready": False, "accuracy": None, "overlap": None, "weak": [], "reason": "needs_two_states"}
    centres = {label: _centroid(rows) for label, rows in usable.items()}
    labels = sorted(centres)
    overlap = max(float(centres[a] @ centres[b]) for i, a in enumerate(labels) for b in labels[i + 1:])
    right = total = 0
    weak = [label for label, rows in usable.items() if len(rows) < MIN_EXAMPLES]
    for label, rows in usable.items():
        for index in range(len(rows)):
            rest = {k: ([r for j, r in enumerate(v) if not (k == label and j == index)]) for k, v in usable.items()}
            if len([k for k, v in rest.items() if v]) < 2:
                continue
            total += 1
            right += classify(rest, rows[index]).label == label
    accuracy = round(right / total, 3) if total else None
    reason = "too_similar" if overlap >= TOO_SIMILAR else "more_examples" if weak else "ok"
    return {"ready": reason == "ok", "accuracy": accuracy, "overlap": round(overlap, 3), "weak": weak, "reason": reason}
