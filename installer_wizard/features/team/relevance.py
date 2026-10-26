import math
import re

from features.team.stopwords import clean_tokens, normalize_text

GENERIC = frozenset(
    "crea creami creare fai fammi fare fare apri aprimi aprire mostra mostrami mostrare metti mettimi mettere aggiungi aggiungere voglio vorrei puoi potresti devi "
    "dammi dimmi vedere guarda nuovo nuova nuovi nuove subito adesso ora grazie favore please create make open show want need give tell start avvia avviare "
    "lancia lanciare usa usare cerca cercare trova trovare nel nella versione".split())
PHRASE_BONUS = 14.0
LEARNED_STEP = 2.0
LEARNED_CAP = 4
STEM = 5
WEIGHTS = {"identity": 3.0, "noun": 4.0, "capability": 1.3, "tool": 1.6, "tool_text": 0.6, "description": 0.9, "keyword": 0.3}


def stem(token: str) -> str:
    return token[:STEM] if len(token) > STEM else token


def query_stems(text: str) -> dict[str, str]:
    return {stem(t): t for t in clean_tokens(text) if t not in GENERIC}


def _stems(text: str) -> set[str]:
    return {stem(t) for t in clean_tokens(text) if t not in GENERIC}


def fields(agent) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {k: set() for k in WEIGHTS}
    out["identity"] |= _stems(agent.id) | _stems(agent.name)
    routing = getattr(agent, "routing", None) or {}
    for noun in routing.get("nouns", []):
        out["noun"] |= _stems(str(noun))
    for cap in agent.capabilities:
        out["capability"] |= _stems(cap)
    for tool in agent.tools:
        out["tool"] |= {stem(p) for p in str(tool["name"]).lower().split("_") if len(p) >= 3}
        out["tool_text"] |= _stems(tool.get("description", ""))
    for widget in agent.widgets:
        out["identity"] |= _stems(widget.get("name", ""))
        for intent in widget.get("intents", []):
            out["noun"] |= _stems(str(intent))
    out["description"] |= _stems(agent.description)
    out["keyword"] |= {stem(k) for k in agent.keywords if k not in GENERIC}
    return out


def document_frequency(indexed: dict[str, dict[str, set[str]]]) -> dict[str, int]:
    seen: dict[str, int] = {}
    for fields_ in indexed.values():
        for token in set().union(*fields_.values()):
            seen[token] = seen.get(token, 0) + 1
    return seen


def rarity(token: str, frequency: dict[str, int], total: int) -> float:
    return math.log(1 + total / max(1, frequency.get(token, 1)))


def phrase_hits(agent, text: str) -> int:
    routing = getattr(agent, "routing", None) or {}
    hits = 0
    for pattern in routing.get("phrases", []):
        try:
            if re.search(pattern, text, re.I):
                hits += 1
        except re.error:
            continue
    return min(2, hits)


def rank(agents: dict, text: str, learned: dict[str, dict[str, int]] | None = None) -> list[tuple[str, float, list[str]]]:
    norm = normalize_text(text)
    wanted = query_stems(text)
    indexed = {aid: fields(a) for aid, a in agents.items()}
    frequency = document_frequency(indexed)
    total = max(1, len(agents))
    results = []
    for aid, agent in agents.items():
        score, why = 0.0, []
        for token, original in wanted.items():
            best, kind = 0.0, ""
            for name, weight in WEIGHTS.items():
                if token in indexed[aid][name]:
                    value = weight * rarity(token, frequency, total)
                    if value > best:
                        best, kind = value, name
            if best:
                if original in agent.keywords or original == agent.id.lower():
                    best *= 1.2
                score += best
                why.append(f"{original}:{kind}")
            for_agent = (learned or {}).get(token, {}).get(aid, 0)
            if for_agent:
                score += LEARNED_STEP * min(for_agent, LEARNED_CAP)
                why.append(f"{original}:appreso")
        hits = phrase_hits(agent, norm)
        if hits:
            score += PHRASE_BONUS * hits
            why.append("frase")
        explicit = re.search(rf"\b{re.escape(agent.id.lower())}\b", norm) or (len(agent.name) > 3 and agent.name.lower() in norm)
        if explicit:
            score += 10.0
            why.append("nome")
        results.append((aid, round(score, 3), why))
    results.sort(key=lambda r: r[1], reverse=True)
    return results
