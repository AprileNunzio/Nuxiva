import native_core

MAX_HYPOTHESES = 8
MAX_WORDS = 256
MAX_TEXT = 4000


def _key(word: str) -> str:
    return "".join(c for c in word if c.isalnum() or c == "'").lower()


def _words(text: str) -> list[tuple[str, str]]:
    out = [(w, _key(w)) for w in text.split()]
    return [w for w in out if w[1]][:MAX_WORDS]


def _align(pivot: list, other: list) -> list[tuple]:
    rows, cols = len(pivot) + 1, len(other) + 1
    cost = [[0] * cols for _ in range(rows)]
    for i in range(rows):
        cost[i][0] = i
    for j in range(cols):
        cost[0][j] = j
    for i, p in enumerate(pivot):
        for j, o in enumerate(other):
            cost[i + 1][j + 1] = min(cost[i][j] + (p[1] != o[1]), cost[i][j + 1] + 1, cost[i + 1][j] + 1)
    i, j, steps = len(pivot), len(other), []
    while i > 0 or j > 0:
        here = cost[i][j]
        if i > 0 and j > 0 and cost[i - 1][j - 1] + (pivot[i - 1][1] != other[j - 1][1]) == here:
            steps.append(("match", i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i > 0 and cost[i - 1][j] + 1 == here:
            steps.append(("delete", i - 1, None))
            i -= 1
        else:
            steps.append(("insert", None, j - 1))
            j -= 1
    steps.reverse()
    return steps


class _Slot:

    def __init__(self) -> None:
        self.options: list[list] = []
        self.empty = 0.0

    def add(self, word: tuple, weight: float) -> None:
        for entry in self.options:
            if entry[0][1] == word[1]:
                entry[1] += weight
                return
        self.options.append([word, weight])

    def winner(self) -> tuple:
        best = None
        for entry in self.options:
            if best is None or entry[1] > best[1]:
                best = entry
        if best is not None and best[1] > self.empty:
            return best[0], best[1]
        return None, self.empty

    def total(self) -> float:
        return sum(w for _, w in self.options) + self.empty


def py_vote(hypotheses: list[tuple[str, float]]) -> tuple[str, float, int]:
    ballots = []
    for text, weight in hypotheses[:MAX_HYPOTHESES]:
        weight = float(weight)
        weight = min(10.0, max(0.0, weight)) if weight == weight and abs(weight) != float("inf") else 0.0
        if weight > 0.0:
            ballots.append((_words(str(text)), weight))
    candidates = [i for i, (ws, _) in enumerate(ballots) if ws]
    if not candidates:
        return "", 0.0, 0
    pivot_index = candidates[0]
    for i in candidates[1:]:
        if ballots[i][1] > ballots[pivot_index][1]:
            pivot_index = i
    pivot, pivot_weight = ballots[pivot_index]
    slots = []
    for word in pivot:
        slot = _Slot()
        slot.add(word, pivot_weight)
        slots.append(slot)
    gaps = [_Slot() for _ in range(len(pivot) + 1)]
    for index, (other, weight) in enumerate(ballots):
        if index == pivot_index:
            continue
        gap_index, filled = 0, [False] * len(gaps)
        for kind, i, j in _align(pivot, other):
            if kind == "match":
                slots[i].add(other[j], weight)
                gap_index = i + 1
            elif kind == "delete":
                slots[i].empty += weight
                gap_index = i + 1
            else:
                gaps[gap_index].add(other[j], weight)
                filled[gap_index] = True
        for gap, was in zip(gaps, filled):
            if not was:
                gap.empty += weight
    for gap in gaps:
        gap.empty += pivot_weight
    out, agreement, columns, changed = [], 0.0, 0, 0
    for index, gap in enumerate(gaps):
        word, _ = gap.winner()
        if word is not None:
            out.append(word[0])
            changed += 1
        if index < len(slots):
            slot = slots[index]
            word, weight = slot.winner()
            total = slot.total()
            if total > 0.0:
                agreement += weight / total
                columns += 1
            if word is None:
                changed += 1
            else:
                if word[1] != pivot[index][1]:
                    changed += 1
                out.append(word[0])
    return " ".join(out), (agreement / columns if columns else 0.0), changed


def vote(hypotheses: list[tuple[str, float]]) -> tuple[str, float, int]:
    clean = [(str(t)[:MAX_TEXT], float(w)) for t, w in hypotheses[:MAX_HYPOTHESES]]
    engine = native_core.symbol("ear_vote")
    if engine is None:
        native_core.python_fallback("ear.vote")
        return py_vote(clean)
    return engine(clean)
