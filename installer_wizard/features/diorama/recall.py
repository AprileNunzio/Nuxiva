import re

from features.diorama import store

THRESHOLD = 0.6
STOP = frozenset({"il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "di", "del", "della", "dei", "con", "in", "su", "per",
                  "a", "e", "the", "an", "of", "with", "on", "for", "and", "light", "luce"})
WORD = re.compile(r"[^\W\d_]{3,}", re.UNICODE)


def tokens(text: str) -> frozenset[str]:
    return frozenset(w[:6] for w in WORD.findall(text.lower()) if w not in STOP)


def score(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b)) * (len(a & b) / len(a | b)) ** 0.5


def find(prompt: str) -> str | None:
    wanted = tokens(prompt)
    best, best_id = 0.0, None
    for row in store.listing():
        try:
            record = store.load(row["id"])
        except KeyError:
            continue
        if not record["items"]:
            continue
        value = score(wanted, tokens(f"{record['prompt']} {record['title']}"))
        if value > best:
            best, best_id = value, record["id"]
    return best_id if best >= THRESHOLD else None
