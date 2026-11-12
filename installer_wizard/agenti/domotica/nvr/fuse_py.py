import json

from agenti.ear.vote import py_vote

MAX_UTTERANCES = 20_000
MAX_TEXT = 4000
UNKNOWN_WEIGHT = 0.5


def _weight(w) -> float:
    w = float(w)
    return min(10.0, max(0.0, w)) if w == w and abs(w) != float("inf") else 0.0


def _overlap(a: tuple, b: tuple) -> float:
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    shorter = max(1, min(a[1] - a[0], b[1] - b[0]))
    return inter / shorter


def _speaker(group: list[dict]) -> tuple[str | None, float]:
    tally: dict[str, list] = {}
    for u in group:
        key = u.get("speaker") or ""
        raw = float(u.get("speaker_score") or 0.0)
        score = min(1.0, max(0.0, raw)) if raw == raw and abs(raw) != float("inf") else 0.0
        gain = UNKNOWN_WEIGHT if not key else score
        entry = tally.setdefault(key, [0.0, 0.0])
        entry[0] += _weight(u["weight"]) * gain
        entry[1] = max(entry[1], score)
    best = None
    for key in sorted(tally):
        if best is None or tally[key][0] > tally[best][0]:
            best = key
    if not best:
        return None, 0.0
    return best, tally[best][1]


def py_fuse(rows: list[dict], min_overlap: float) -> list[dict]:
    if len(rows) > MAX_UTTERANCES or any(len(str(u["text"]).encode()) > MAX_TEXT for u in rows):
        raise ValueError("nvr.catalog.too_many")
    ordered = sorted((u for u in rows if u["end_ms"] > u["start_ms"] and str(u["text"]).strip()),
                     key=lambda u: (u["start_ms"], u["end_ms"], u["source"]))
    groups: list[list[dict]] = []
    for u in ordered:
        span = (u["start_ms"], u["end_ms"])
        target = None
        for g in reversed(groups[-8:]):
            box = (min(x["start_ms"] for x in g), max(x["end_ms"] for x in g))
            if all(x["source"] != u["source"] for x in g) and _overlap(box, span) >= min_overlap:
                target = g
                break
        if target is None:
            groups.append([u])
        else:
            target.append(u)
    turns = []
    for g in groups:
        text, agreement, changed = py_vote([(str(u["text"]), _weight(u["weight"])) for u in g])
        if not text:
            continue
        speaker, score = _speaker(g)
        turns.append({"start_ms": min(u["start_ms"] for u in g), "end_ms": max(u["end_ms"] for u in g), "text": text,
                      "speaker": speaker, "speaker_score": score, "agreement": agreement, "changed": changed,
                      "sources": sorted(u["source"] for u in g)})
    return turns


def py_fuse_json(rows_json: str, min_overlap: float) -> str:
    return json.dumps(py_fuse(json.loads(rows_json), max(0.0, min(1.0, min_overlap))))
