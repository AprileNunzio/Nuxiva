import hashlib
import json
import os
import re
import threading
import time
from pathlib import Path

from config import STATE_DIR

MAX_TURNS = 64
MAX_SHINGLES = 256
KEEP_FOR = 7 * 24 * 3600
_lock = threading.Lock()


def shingles(text: str) -> list[int]:
    words = re.findall(r"\w+", text.lower())
    grams = {" ".join(words[i:i + 3]) for i in range(max(0, len(words) - 2))} or set(words)
    return sorted({int(hashlib.sha256(g.encode("utf-8")).hexdigest()[:12], 16) for g in grams})[:MAX_SHINGLES]


def similarity(a: list[int], b: list[int]) -> float:
    left, right = set(a), set(b)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


class Ledger:
    def __init__(self, path: Path) -> None:
        self.path = path

    def turns(self) -> list[dict]:
        with _lock:
            return self._read()

    def _read(self) -> list[dict]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        except (OSError, ValueError) as exc:
            from state import store
            store.event("WARN", f"Registro dei resoconti illeggibile, lo ricomincio: {exc}", "checkin")
            self.path.unlink(missing_ok=True)
            return []
        now = time.time()
        return [t for t in raw.get("turns", []) if isinstance(t, dict) and now - float(t.get("at", 0)) <= KEEP_FOR][-MAX_TURNS:]

    def record(self, told: list[str], style: str, humor: bool, speech: str) -> None:
        turn = {"at": int(time.time()), "told": told[:64], "style": style[:40], "humor": bool(humor), "shingles": shingles(speech)}
        with _lock:
            turns = (self._read() + [turn])[-MAX_TURNS:]
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"turns": turns}), encoding="utf-8")
            os.chmod(tmp, 0o600)
            tmp.replace(self.path)

    def too_similar(self, speech: str, limit: float, last: int = 5) -> bool:
        mine = shingles(speech)
        return any(similarity(mine, t.get("shingles") or []) >= limit for t in self.turns()[-last:])


ledger = Ledger(STATE_DIR / "checkin" / "turns.json")
