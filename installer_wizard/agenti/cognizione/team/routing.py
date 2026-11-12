import hashlib
import json
import logging
import os
import threading

from agenti.team import relevance
from agenti.team.stopwords import clean_tokens, is_conversational_query, normalize_text

log = logging.getLogger("nuxiva.team.routing")
MIN_SCORE = 5.0
SUPPORT_RATIO = 0.55
SUPPORT_SLOTS = 3
STRONG_SCORE = 18.0
STRONG_MARGIN = 0.3
LIGHT_RISK = 2
LAMPO, STANDARD, PROGETTO = "lampo", "standard", "progetto"


def _risk(agent) -> int:
    try:
        from agenti.authz import risk
    except ImportError:
        return 4 if agent.tools else 0
    return max((int(risk.of_tool(str(t.get("name", "")))) for t in agent.tools), default=0)


def card(agent) -> dict:
    routing = getattr(agent, "routing", None) or {}
    profile = getattr(agent, "profile", None) or {}
    return {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "keywords": sorted(agent.keywords),
        "capabilities": list(agent.capabilities),
        "tools": [{"name": str(t.get("name", "")), "description": str(t.get("description", ""))} for t in agent.tools],
        "widgets": [{"name": str(w.get("name", "")), "intents": [str(i) for i in w.get("intents", [])]} for w in agent.widgets],
        "nouns": [str(n) for n in routing.get("nouns", [])],
        "phrases": [str(p) for p in routing.get("phrases", [])],
        "heavy": profile.get("heavy") is True,
        "project": profile.get("project") is True,
        "risk": _risk(agent),
    }


def level(primary: dict | None, supports: int) -> str:
    if primary is None:
        return LAMPO
    if primary["project"]:
        return PROGETTO
    if primary["heavy"] or supports > 0 or primary["risk"] > LIGHT_RISK:
        return STANDARD
    return LAMPO


def needs_reasoning(ranked: list) -> bool:
    if not ranked:
        return False
    top = ranked[0][1]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    return not (top >= STRONG_SCORE and (top - second) / max(top, 1.0) >= STRONG_MARGIN)


def _empty(conversational: bool, confidence: float, ranked: list) -> dict:
    return {"conversational": conversational, "primary": "", "secondaries": [], "confidence": confidence, "heavy": False,
            "level": LAMPO, "needs_reasoning": needs_reasoning(ranked) if not conversational else False, "ranked": ranked}


def decide_py(agents: dict, cards: dict, text: str, learned: dict) -> dict:
    text = text[:relevance.MAX_QUERY]
    if is_conversational_query(normalize_text(text)) or not clean_tokens(text):
        return _empty(True, 1.0, [])
    ranked = relevance.rank(agents, text, learned)
    if not ranked or ranked[0][1] < MIN_SCORE:
        return _empty(False, 0.5, ranked)
    top_id, top, _ = ranked[0]
    runner = ranked[1][1] if len(ranked) > 1 else 0.0
    supports = [aid for aid, sc, _ in ranked[1:1 + SUPPORT_SLOTS] if sc >= top * SUPPORT_RATIO and sc >= MIN_SCORE]
    margin = (top - runner) / max(top, 1.0)
    primary = cards.get(top_id)
    return {"conversational": False, "primary": top_id, "secondaries": supports,
            "confidence": round(min(1.0, 0.55 + min(top, 30.0) / 30.0 * 0.25 + margin * 0.2), 3),
            "heavy": bool(primary and primary["heavy"]), "level": level(primary, len(supports)),
            "needs_reasoning": needs_reasoning(ranked), "ranked": ranked}


def _factory():
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustCeoIndex", None)


class Router:
    def __init__(self, native: bool = True) -> None:
        self._lock = threading.Lock()
        self._factory = _factory() if native else None
        self._key = ""
        self._cards: dict[str, dict] = {}
        self._index = None
        self._learned_key: object = None

    @property
    def engine(self) -> str:
        return "rust" if self._factory is not None else "python"

    def cards(self, agents: dict) -> dict[str, dict]:
        built = {aid: card(a) for aid, a in agents.items()}
        payload = json.dumps(list(built.values()), ensure_ascii=False, separators=(",", ":"))
        key = hashlib.sha256(payload.encode()).hexdigest()
        with self._lock:
            if key != self._key:
                self._key, self._cards, self._learned_key = key, built, None
                self._index = self._build(payload)
            return self._cards

    def _build(self, payload: str):
        if self._factory is None:
            return None
        try:
            index = self._factory(payload)
        except (ValueError, RuntimeError) as exc:
            log.warning("indice CEO nativo non disponibile: %s", exc)
            return None
        for agent_id, pattern in index.invalid_phrases():
            log.warning("frase di instradamento non valida per %s: %s", agent_id, pattern[:80])
        return index

    def decide(self, agents: dict, text: str, learned: dict, learned_version: object = None) -> dict:
        cards = self.cards(agents)
        index = self._index
        if index is None:
            return decide_py(agents, cards, text, learned)
        try:
            with self._lock:
                stamp = (learned_version, len(learned)) if learned_version is not None else object()
                if stamp != self._learned_key:
                    index.set_learned(json.dumps(learned, ensure_ascii=False, separators=(",", ":")))
                    self._learned_key = stamp
            raw = json.loads(index.decide(text))
        except (ValueError, RuntimeError) as exc:
            log.warning("decisione CEO nativa fallita, uso Python: %s", exc)
            return decide_py(agents, cards, text, learned)
        raw["ranked"] = [(r["id"], r["score"], r["why"]) for r in raw["ranked"]]
        return raw


router = Router()
