import re

SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
HOUSEHOLD = ("owner", "family")
MAX_PEOPLE = 64


def _slug(value) -> str | None:
    return value if isinstance(value, str) and SLUG.match(value) else None


def emergency_of(profile: dict | None) -> list[str]:
    entries = (profile or {}).get("emergency")
    if not isinstance(entries, list):
        return []
    out: list[str] = []
    for entry in entries[:MAX_PEOPLE]:
        slug = _slug(entry.get("person")) if isinstance(entry, dict) else None
        if slug and slug not in out:
            out.append(slug)
    return out


def household(profiles: list[dict]) -> list[str]:
    ranked = sorted(
        (p for p in profiles if isinstance(p, dict) and _slug(p.get("slug")) and p.get("role") in HOUSEHOLD),
        key=lambda p: (HOUSEHOLD.index(p["role"]), str(p.get("first_name") or ""), p["slug"]),
    )
    return [p["slug"] for p in ranked][:MAX_PEOPLE]


def plan(profiles: list[dict], subject: str | None, tiers: int) -> list[list[str]]:
    known = {p.get("slug"): p for p in profiles if isinstance(p, dict) and _slug(p.get("slug"))}
    subject = _slug(subject) if subject in known else None
    house = [s for s in household(profiles) if s != subject]
    first = [s for s in emergency_of(known.get(subject)) if s in known and s != subject]
    primary = first + [s for s in house if s not in first]
    extended: list[str] = []
    for slug in house:
        for other in emergency_of(known.get(slug)):
            if other in known and other != subject and other not in primary and other not in extended:
                extended.append(other)
    out = [primary]
    for _ in range(1, max(1, tiers)):
        out.append(extended or primary)
    return out


def everyone(levels: list[list[str]]) -> list[str]:
    seen: list[str] = []
    for level in levels:
        for slug in level:
            if slug not in seen:
                seen.append(slug)
    return seen
