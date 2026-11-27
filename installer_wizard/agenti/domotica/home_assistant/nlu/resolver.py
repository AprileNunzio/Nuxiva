import json
import logging
import threading
from pathlib import Path

import native_core

from agenti.home_assistant.nlu.calls import build_call, is_sensitive

log = logging.getLogger("nuxiva.home.resolve")
MAX_TEXT_BYTES = 600
MAX_NAME_BYTES = 200
MAX_ALIASES = 32
LANGUAGES = {"it", "en", "es", "fr"}
_lock = threading.Lock()


def messages(language: str = "it") -> dict:
    language = language if language in LANGUAGES else "it"
    path = Path(__file__).resolve().parent.parent / "language" / f"{language}.json"
    return json.loads(path.read_text(encoding="utf-8"))["resolve"]


def _clip(text: str, limit: int) -> str:
    return str(text or "").encode("utf-8")[:limit].decode("utf-8", "ignore")


def _labels(names, main: str) -> list[str]:
    seen = {_clip(main, MAX_NAME_BYTES)}
    out = []
    for name in names or []:
        label = _clip(name, MAX_NAME_BYTES)
        if label and label not in seen:
            seen.add(label)
            out.append(label)
    return out[:MAX_ALIASES]


def inventory(cat) -> dict:
    areas = [{"id": _clip(aid, MAX_NAME_BYTES), "name": _clip(a["name"], MAX_NAME_BYTES), "aliases": _labels(a.get("labels"), a["name"])}
             for aid, a in cat.areas.items()]
    entities = [{"id": e["entity_id"], "domain": e["domain"], "name": _clip(e["name"], MAX_NAME_BYTES),
                 "aliases": _labels(e.get("labels"), e["name"]), "area": e.get("area_id"), "device": e.get("device_id"),
                 "group": bool(e.get("is_group")), "as_light": bool(e.get("as_light"))}
                for e in cat.controllable()
                if len(e["entity_id"]) <= MAX_NAME_BYTES and e["entity_id"].startswith(f"{e['domain']}.")]
    return {"areas": areas, "entities": entities}


def engine(cat):
    if cat.resolver is not None:
        return cat.resolver or None
    factory = native_core.symbol("RustHomeResolver")
    with _lock:
        if cat.resolver is not None:
            return cat.resolver or None
        if factory is None:
            native_core.python_fallback("home.resolve")
            cat.resolver = False
            return None
        try:
            cat.resolver = factory(json.dumps(inventory(cat)))
        except ValueError as exc:
            log.warning("Inventario della casa non utilizzabile per il ragionamento: %s", exc)
            cat.resolver = False
    return cat.resolver or None


def resolve(text: str, cat, here: str | None = None) -> dict | None:
    resolver = engine(cat)
    if resolver is None:
        return None
    request = {"text": _clip(text, MAX_TEXT_BYTES), "here": here, "fallback": cat.default_area}
    try:
        return json.loads(resolver.resolve(json.dumps(request)))
    except ValueError as exc:
        log.info("Ragionamento domotico non riuscito: %s", exc)
        return None


def relevance(text: str, cat) -> dict | None:
    resolver = engine(cat)
    if resolver is None:
        return None
    try:
        return json.loads(resolver.relevance(json.dumps({"text": _clip(text, MAX_TEXT_BYTES)})))
    except ValueError as exc:
        log.info("Pertinenza domotica non valutabile: %s", exc)
        return None


def _join(items: list[str], word: str) -> str:
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} {word} {items[-1]}"


def _rooms(res: dict, text: dict) -> str:
    return _join(res.get("rooms") or [], text["and"])


def plan(text: str, cat, params: dict, here: str | None = None, language: str = "it") -> dict | None:
    res = resolve(text, cat, here)
    if not res or res["decision"] == "none":
        return None
    words = messages(language)
    if res["decision"] == "clarify":
        rooms = res.get("rooms") or []
        speech = words["which_room"].format(rooms=_join(rooms[:4], words["and"])) if rooms else words["which_room_plain"]
        return {"kind": "ask", "speech": speech}
    if res["decision"] == "missing":
        speech = words["none_in_room"].format(rooms=_rooms(res, words)) if res.get("rooms") else words["none_anywhere"]
        return {"kind": "ask", "speech": speech}
    calls: dict = {}
    targets, sensitive = [], False
    for call in res["calls"]:
        e = cat.entities.get(call["entity"])
        built = build_call(call["action"], e, params) if e else None
        if built is None:
            continue
        service, data = built
        sensitive = sensitive or is_sensitive(e["domain"], service, e)
        key = (e["domain"], service, tuple(sorted((k, str(v)) for k, v in data.items())))
        calls.setdefault(key, {"domain": e["domain"], "service": service, "entity_ids": [], "data": data})
        calls[key]["entity_ids"].append(e["entity_id"])
        targets.append(e["entity_id"])
    if not calls:
        return None
    names = _join([cat.entities[t]["name"] for t in targets[:4]], words["and"])
    what = f"{words['verbs'].get(res['action'], res['action'])} {names}"
    return {"kind": "command", "action": res["action"], "calls": list(calls.values()), "entities": targets,
            "area_ids": res.get("areas") or [], "how": f"ragionamento · {res['how']}", "confidence": res["confidence"],
            "confirm": res["decision"] == "confirm", "question": words["confirm"].format(what=what),
            "params": {k: v for k, v in params.items() if k != "rgb"}, "sensitive": sensitive}
