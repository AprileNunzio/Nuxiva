import math
import re
import time
from copy import deepcopy

SCOPES = {"personal", "shared", "unassigned"}
ORIGINS = {"conversation", "manual", "legacy", "diary"}
IDENTITY = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")


class MemoryInputError(ValueError):
    pass


def number(value, low: float = 0, high: float = float("inf")) -> float:
    if isinstance(value, bool):
        raise MemoryInputError("invalid_memory")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise MemoryInputError("invalid_memory") from exc
    if not math.isfinite(result) or not low <= result <= high:
        raise MemoryInputError("invalid_memory")
    return result


def expiry(value) -> float | None:
    return None if value is None else number(value, low=1)


def content(value) -> str:
    if not isinstance(value, str):
        raise MemoryInputError("invalid_memory")
    text = " ".join(value.split())
    if not 3 <= len(text) <= 200 or any(ord(c) < 32 for c in text):
        raise MemoryInputError("invalid_memory")
    return text


def metadata(who: str, scope: str | None, origin: str, expires_at) -> dict:
    if not isinstance(who, str) or who and not IDENTITY.fullmatch(who):
        raise MemoryInputError("invalid_memory")
    scope = ("personal" if who else "unassigned") if scope is None else scope
    if not isinstance(scope, str) or not isinstance(origin, str) or scope not in SCOPES or \
            scope == "personal" and not who or origin not in ORIGINS:
        raise MemoryInputError("invalid_memory")
    return {"who": who, "scope": scope, "origin": origin, "expires_at": expiry(expires_at)}


def limbic_state(value) -> dict:
    defaults = {"valence": 0.0, "arousal": 0.3, "dopamine": 0.5, "noradrenaline": 0.2}
    if value is not None and not isinstance(value, dict):
        raise MemoryInputError("invalid_memory")
    return {key: number((value or {}).get(key, default), -1 if key == "valence" else 0, 1)
            for key, default in defaults.items()}


def active(fact: dict, now: float | None = None) -> bool:
    return fact.get("expires_at") is None or fact["expires_at"] > (time.time() if now is None else now)


def validate_facts(data) -> list:
    if not isinstance(data, list):
        raise MemoryInputError("invalid_memory")
    facts = []
    ids = set()
    for raw in data:
        if not isinstance(raw, dict) or not isinstance(raw.get("text"), str) or not raw.get("id") or raw["id"] in ids:
            raise MemoryInputError("invalid_memory")
        fact = deepcopy(raw)
        who = fact.get("who") or ""
        fact.update(metadata(who, fact.get("scope"), fact.get("origin", "legacy"), fact.get("expires_at")))
        fact.setdefault("kind", "fatto")
        fact.setdefault("score", 0.6)
        fact.setdefault("created", 0.0)
        fact.setdefault("updated", fact["created"])
        fact.setdefault("hits", 0)
        fact.setdefault("revision", 1)
        fact.setdefault("history", [])
        if not isinstance(fact["revision"], int) or isinstance(fact["revision"], bool) or fact["revision"] < 1:
            raise MemoryInputError("invalid_memory")
        fact["score"] = number(fact["score"], 0, 1)
        fact["created"], fact["updated"] = number(fact["created"]), number(fact["updated"])
        for key in ("hits", "rehearsals"):
            fact[key] = int(number(fact.get(key, 0)))
        fact["limbic"] = limbic_state(fact.get("limbic"))
        if not isinstance(fact["history"], list):
            raise MemoryInputError("invalid_memory")
        facts.append(fact)
        ids.add(fact["id"])
    return facts


def validate_state(data) -> dict:
    if not isinstance(data, dict):
        raise MemoryInputError("invalid_memory")
    return data
