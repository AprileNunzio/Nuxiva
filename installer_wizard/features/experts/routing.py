import re
import unicodedata

from features.experts import templates
from features.experts.model import Expert

STEM = 5
ASK_EXPERT = re.compile(r"\b(chiedi|domanda|passa|fai\s+rispondere|senti)\b.{0,30}\b(all'?|a\s+un\s+|al\s+|l'?)?esperto\b|\besperto\s+(di|in|del|della|dei)\b")


def flat(text: str) -> str:
    plain = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", plain).strip()


def _terms(expert: Expert) -> set[str]:
    words = re.findall(r"[a-z]{5,}", flat(f"{expert.role} {expert.specialty} {' '.join(expert.knowledge)}"))
    terms = {w[:STEM] for w in words}
    terms.update(flat(k) for k in templates.keywords(expert.template))
    return terms


def score(expert: Expert, text: str) -> int:
    body = flat(text)
    return sum(1 for term in _terms(expert) if term and term in body)


def addressed(experts: list[Expert], text: str) -> Expert | None:
    body = flat(text)
    for expert in experts:
        name = re.escape(flat(expert.name))
        if re.match(rf"^(ehi\s+|ciao\s+)?{name}\b", body) or re.search(rf"\b(chiedi|domanda|passa)\s+(a|ad)\s+{name}\b", body):
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
