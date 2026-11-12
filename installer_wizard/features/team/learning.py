import json
import threading

from config import STATE_DIR
from sealed import write_private
from features.team.relevance import LEARNED_CAP, query_stems

FILE = STATE_DIR / "team" / "learned.json"
MAX_STEMS = 4000
lock = threading.Lock()
cache: dict | None = None


def _load() -> dict[str, dict[str, int]]:
    global cache
    if cache is None:
        try:
            raw = json.loads(FILE.read_text(encoding="utf-8"))
            cache = {str(k): {str(a): int(n) for a, n in v.items()} for k, v in raw.items() if isinstance(v, dict)}
        except (OSError, ValueError, AttributeError, TypeError):
            cache = {}
    return cache


def table() -> dict[str, dict[str, int]]:
    with lock:
        return _load()


def reset() -> None:
    global cache
    with lock:
        cache = None


def record(text: str, agent_id: str) -> int:
    stems = list(query_stems(text))
    if not stems or not agent_id:
        return 0
    with lock:
        data = _load()
        for token in stems:
            row = data.setdefault(token, {})
            row[agent_id] = min(LEARNED_CAP * 3, row.get(agent_id, 0) + 1)
        while len(data) > MAX_STEMS:
            data.pop(next(iter(data)))
        try:
            FILE.parent.mkdir(parents=True, exist_ok=True)
            write_private(FILE, json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode())
        except OSError:
            return 0
    return len(stems)
