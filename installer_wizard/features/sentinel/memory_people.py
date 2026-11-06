import logging
import re
import time

from features.sentinel import record
from features.sentinel.journal import SentinelUnavailable
from features.sentinel.memory import memory

log = logging.getLogger("nuxiva.sentinel.memory")
KEY = "sentinel_memory"
GUEST = re.compile(r"^(?:ospite|guest)-(\d{1,5})$")
GENERIC = re.compile(r"^(?:ospite|guest|sconosciuto|unknown)(?:\s+\d+)?$", re.I)


def _profile(slug: str) -> dict | None:
    from features.people import people
    return people.load(slug)


def who_for(slug: str, profile: dict | None = None) -> dict | None:
    profile = profile if profile is not None else _profile(slug)
    if profile is None:
        return None
    match = GUEST.match(str(profile.get("slug") or slug))
    name = str(profile.get("name") or "").strip()
    if match and (not name or GENERIC.match(name)) and 0 < int(match.group(1)) < 65536:
        return {"type": "guest", "id": int(match.group(1))}
    return {"type": "person", "id": record.pseudonym(str(profile.get("slug") or slug))}


def allows_details(profile: dict | None) -> bool:
    return bool(profile is None or profile.get("consent", True)) and record.option("NUXIVA_SENTINEL_APPEARANCE")


def sync(slug: str) -> dict | None:
    from features.people import people
    profile = _profile(slug)
    who = who_for(slug, profile)
    if who is None:
        return None
    summary = {**memory.profile(who), "updated_at": time.time()}
    with people._lock:
        current = people.load(slug)
        if current is None:
            return None
        current[KEY] = summary
        people.save(current)
    return summary


def forget(slug: str, profile: dict | None = None) -> int:
    who = who_for(slug, profile)
    if who is None:
        return 0
    try:
        removed = memory.forget(who)
    except SentinelUnavailable:
        return 0
    record.record("sentinel.read", record.NUXIVA, "sentinel.sentinel.memory_forget", {"count": removed}, "household",
                  "sentinel")
    return removed


def associate(source: dict | None, to_slug: str) -> int:
    if source is None:
        return 0
    target = who_for(to_slug)
    if target is None or target == source:
        return 0
    try:
        moved = memory.relink(source, target)
    except SentinelUnavailable:
        return 0
    if moved:
        record.record("sentinel.read", record.NUXIVA, "sentinel.sentinel.memory_relink", {"count": moved},
                      "household", "sentinel")
        sync(to_slug)
    return moved
