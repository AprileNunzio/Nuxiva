import re
import unicodedata
from dataclasses import dataclass

from features.experts import templates
from features.experts.model import Expert

STEM = 5
HEAVY = 6
DELEGATE_MIN = 2
SHORTLIST = 3
ASK_EXPERT = re.compile(r"\b(chiedi|domanda|passa|fai\s+rispondere|senti)\b.{0,30}\b(all'?|a\s+un\s+|al\s+|l'?)?esperto\b|\besperto\s+(di|in|del|della|dei)\b")


def flat(text: str) -> str:
    plain = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", plain).strip()


@dataclass(frozen=True)
class Delegation:
    expert: Expert
    score: int
    shortlist: tuple[str, ...]


def _terms(expert: Expert) -> set[str]:
    curated = {flat(k) for k in templates.keywords(expert.template)}
    if curated:
        return {k for k in curated if k}
    words = re.findall(r"[a-z]{5,}", flat(f"{expert.role} {expert.specialty} {' '.join(expert.knowledge)}"))
    return {w[:STEM] for w in words}


def _weight(term: str) -> int:
    return 2 if len(term.strip()) >= HEAVY else 1


def score(expert: Expert, text: str) -> int:
    body = flat(text)
    return sum(_weight(t) for t in _terms(expert) if re.search(rf"(?<![a-z0-9]){re.escape(t)}", body))


def choose(experts: list[Expert], text: str, minimum: int = DELEGATE_MIN) -> Delegation | None:
    ranked = sorted(((score(e, text), e.created, e) for e in experts if e.enabled), key=lambda r: (-r[0], r[1]))
    if not ranked or ranked[0][0] < minimum:
        return None
    top = ranked[0][0]
    return Delegation(ranked[0][2], top, tuple(e.role for s, _, e in ranked[1:SHORTLIST + 1] if s >= minimum and s >= top * 0.6))


def addressed(experts: list[Expert], text: str) -> Expert | None:
    body = flat(text)
    for expert in sorted(experts, key=lambda e: -len(e.role)):
        role = re.escape(flat(expert.role))
        if re.search(rf"(^|\b)(ehi\s+|ciao\s+|chiedi\s+(a\s+|al\s+|all')?)?{role}\b", body):
            return expert
    return None


def best(experts: list[Expert], text: str, minimum: int = 1) -> Expert | None:
    ranked = sorted(((score(e, text), e.created, e) for e in experts if e.enabled), key=lambda r: (-r[0], r[1]))
    return ranked[0][2] if ranked and ranked[0][0] >= minimum else None


def route(experts: list[Expert], text: str) -> Expert | None:
    live = [e for e in experts if e.enabled]
    direct = addressed(live, text)
    if direct:
        return direct
    if ASK_EXPERT.search(flat(text)):
        return best(live, text)
    return None
