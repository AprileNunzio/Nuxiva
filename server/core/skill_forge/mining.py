import hashlib
import math
from typing import Sequence

SIMILARITY = 0.80
MIN_CLUSTER = 5
MAX_PROMPT_EXAMPLES = 12


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    norm = math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right))
    return dot / norm if norm else 0.0


def cluster(texts: Sequence[str], vectors: Sequence[Sequence[float]], threshold: float = SIMILARITY,
            minimum: int = MIN_CLUSTER) -> list[list[str]]:
    leaders: list[Sequence[float]] = []
    groups: list[list[str]] = []
    for text, vector in zip(texts, vectors):
        best, best_score = -1, threshold
        for index, leader in enumerate(leaders):
            score = _cosine(leader, vector)
            if score >= best_score:
                best, best_score = index, score
        if best < 0:
            leaders.append(vector)
            groups.append([text])
        else:
            groups[best].append(text)
    return sorted((group for group in groups if len(group) >= minimum), key=len, reverse=True)


def examples(group: Sequence[str]) -> list[str]:
    unique = list(dict.fromkeys(item.strip() for item in group if item.strip()))
    return unique[:MAX_PROMPT_EXAMPLES]


def key(group: Sequence[str]) -> str:
    basis = "\n".join(sorted(item.lower() for item in examples(group))[:5])
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:24]
