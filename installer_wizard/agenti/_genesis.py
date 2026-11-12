import json
import os

from ._registry import AgentRegistry, registry as default_registry

ENHANCE_SCORE = 4
SIMILAR_SCORE = 2
MAX_LISTED = 5


def _native():
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "agent_genesis_decide", None)


def verdict(hits: list[tuple[str, int]], id_taken: bool, motive: bool) -> dict:
    fn = _native()
    if fn is not None:
        payload = {"hits": [{"id": i, "score": int(n)} for i, n in hits[:256]], "id_taken": id_taken, "motive": motive}
        return json.loads(fn(json.dumps(payload, ensure_ascii=False)))
    similar = sorted(({"id": i, "score": int(n)} for i, n in hits[:256] if int(n) >= SIMILAR_SCORE),
                     key=lambda h: (-h["score"], h["id"]))[:MAX_LISTED]
    top = similar[0] if similar else None
    if id_taken:
        action, target, creatable, reason = "potenzia", "", False, "id_taken"
    elif top is not None and top["score"] >= ENHANCE_SCORE:
        action, target, creatable, reason = "potenzia", top["id"], False, "strong_match"
    elif top is not None:
        action, target, creatable, reason = "verifica", top["id"], motive, "weak_match"
    else:
        action, target, creatable, reason = "crea", "", True, "no_match"
    return {"action": action, "target": target, "similar": similar, "creatable": creatable, "reason": reason}


def decide(spec: dict, motive: str = "", registry: AgentRegistry = default_registry) -> dict:
    text = " ".join([str(spec.get("name", "")), str(spec.get("description", "")),
                     *map(str, spec.get("capabilities", [])), *map(str, spec.get("nouns", []))])
    ident = str(spec.get("id", ""))
    taken = registry.get(ident) is not None or registry.locate_package(ident) is not None
    return verdict(registry.search(text, 16), taken, bool(motive.strip()))
