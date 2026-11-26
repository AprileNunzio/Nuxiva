import json
import time
from collections import deque
from pathlib import Path

MAX_TRACES = 100
LANGUAGE = Path(__file__).resolve().parent / "language"
_traces: deque = deque(maxlen=MAX_TRACES)
_messages: dict[str, dict] = {}


def add(kind: str, public: dict, **extra) -> None:
    _traces.appendleft({"kind": kind, "at": int(time.time() * 1000), **public, **extra})


def recent(limit: int = 50) -> list[dict]:
    return list(_traces)[:max(1, min(limit, MAX_TRACES))]


def message(key: str, lang: str) -> str:
    if lang not in _messages:
        path = LANGUAGE / f"{lang}.json"
        if not path.exists():
            path = LANGUAGE / "en.json"
        _messages[lang] = json.loads(path.read_text(encoding="utf-8")).get("messages", {})
    return _messages[lang].get(key, key)
