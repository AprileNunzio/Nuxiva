import json
import math
import os
import re
import threading
import time
from pathlib import Path

from config import STATE_DIR

TIERS = 10
MAX_ATTEMPTS = 400
WINDOW = 5
PASS_MIN = 3
PASS_MEAN = 0.7
STALE_SECS = 30 * 86_400
LAPSE_SECS = 90 * 86_400
MAX_LESSONS = 100
MAX_LESSON_TEXT = 300
MAX_FILE = 512 * 1024
ROOT = Path(os.environ.get("NUXIVA_MASTERY_DIR", str(STATE_DIR / "mastery")))
NAME = re.compile(r"^[a-z0-9_]{1,48}$")
RANKS = ((0, "novice"), (2, "apprentice"), (4, "proficient"), (6, "advanced"), (8, "expert"))


class MasteryError(ValueError):
    pass


def rank(level: int) -> str:
    for top, name in RANKS:
        if level <= top:
            return name
    return "master"


def _native():
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    return nuxiva_native if hasattr(nuxiva_native, "mastery_evaluate") else None


def _clean(raw: list[dict]) -> list[dict]:
    out = []
    for item in raw[-MAX_ATTEMPTS:]:
        tier, score, at = item.get("tier"), item.get("score"), item.get("at")
        if not isinstance(tier, int) or isinstance(tier, bool) or not 0 <= tier < TIERS or not isinstance(at, int):
            continue
        number = float(score) if isinstance(score, (int, float)) and math.isfinite(score) else 0.0
        out.append({"tier": tier, "score": min(1.0, max(0.0, number)), "at": at})
    return out


def _window(items: list[dict], tier: int) -> list[dict]:
    return [a for a in items if a["tier"] == tier][-WINDOW:]


def _passed(items: list[dict], tier: int, now: int):
    recent = _window(items, tier)
    if len(recent) < PASS_MIN:
        return None
    last = max(a["at"] for a in recent)
    average = sum(a["score"] for a in recent) / len(recent)
    return last if average >= PASS_MEAN and now - last <= LAPSE_SECS else None


def evaluate_python(attempts: list[dict], now: int) -> dict:
    items = _clean(attempts)
    stamps = []
    for tier in range(TIERS):
        at = _passed(items, tier, now)
        if at is None:
            break
        stamps.append(at)
    level = len(stamps)
    stale = [(at, tier) for tier, at in enumerate(stamps) if now - at > STALE_SECS]
    if stale:
        nxt = {"tier": min(stale)[1], "kind": "review"}
    elif level >= TIERS:
        nxt = {"tier": TIERS - 1, "kind": "maintain"}
    else:
        nxt = {"tier": level, "kind": "advance"}
    tail = items[-WINDOW:]
    return {"level": level, "rank": rank(level), "attempts": len(items),
            "recent_mean": sum(a["score"] for a in tail) / len(tail) if tail else 0.0, "next": nxt}


def evaluate(attempts: list[dict], now: int | None = None) -> dict:
    stamp = int(time.time()) if now is None else int(now)
    lib = _native()
    if lib is not None:
        try:
            return json.loads(lib.mastery_evaluate(json.dumps(_clean(attempts)), stamp))
        except ValueError as exc:
            raise MasteryError(str(exc)) from exc
    return evaluate_python(attempts, stamp)


def _name(value: str) -> str:
    if not isinstance(value, str) or not NAME.match(value):
        raise MasteryError("invalid_name")
    return value


class Ledger:
    def __init__(self, root: Path = ROOT) -> None:
        self.root = Path(root)
        self.lock = threading.Lock()

    def _path(self, agent: str) -> Path:
        return self.root / f"{_name(agent)}.json"

    def _load(self, agent: str) -> dict:
        path = self._path(agent)
        try:
            if path.stat().st_size > MAX_FILE:
                return {"topics": {}, "lessons": []}
            data = json.loads(path.read_text("utf-8"))
        except (OSError, ValueError):
            return {"topics": {}, "lessons": []}
        topics = data.get("topics") if isinstance(data, dict) else None
        lessons = data.get("lessons") if isinstance(data, dict) else None
        return {"topics": topics if isinstance(topics, dict) else {}, "lessons": lessons if isinstance(lessons, list) else []}

    def _save(self, agent: str, data: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(agent)
        tmp = path.with_suffix(f".{os.getpid()}.tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, path)

    def record(self, agent: str, topic: str, tier: int, score: float, lesson: str = "", now: int | None = None) -> dict:
        _name(topic)
        if isinstance(tier, bool) or not isinstance(tier, int) or not 0 <= tier < TIERS:
            raise MasteryError("invalid_tier")
        stamp = int(time.time()) if now is None else int(now)
        value = float(score) if isinstance(score, (int, float)) and math.isfinite(score) else 0.0
        with self.lock:
            data = self._load(agent)
            entry = data["topics"].setdefault(topic, [])
            entry.append({"tier": tier, "score": round(min(1.0, max(0.0, value)), 4), "at": stamp})
            del entry[:-MAX_ATTEMPTS]
            text = " ".join(str(lesson or "").split())[:MAX_LESSON_TEXT]
            if text:
                data["lessons"].append({"topic": topic, "tier": tier, "at": stamp, "text": text})
                del data["lessons"][:-MAX_LESSONS]
            self._save(agent, data)
        return self.standing(agent, topic, stamp)

    def standing(self, agent: str, topic: str, now: int | None = None) -> dict:
        _name(topic)
        with self.lock:
            attempts = self._load(agent)["topics"].get(topic, [])
        return evaluate(attempts if isinstance(attempts, list) else [], now)

    def topics(self, agent: str) -> list[str]:
        with self.lock:
            return sorted(key for key in self._load(agent)["topics"] if NAME.match(key))

    def lessons(self, agent: str, limit: int = 10) -> list[dict]:
        with self.lock:
            return list(self._load(agent)["lessons"][-max(0, min(limit, MAX_LESSONS)):])


ledger = Ledger()
