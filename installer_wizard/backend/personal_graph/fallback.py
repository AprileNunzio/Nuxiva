import json
import time

from personal_graph import reads, writes
from personal_graph.graph import KINDS, LEVELS, ORIGINS, GraphFault, Part, clean, fault

MAX_REQUEST = 256 * 1024
UNSUPPORTED = {"extract", "ingest", "observe", "consolidate", "persist", "restore"}
SELF_REF = {"kind": "person", "label": "@self"}


def person_id(value) -> str:
    ok = isinstance(value, str) and 0 < len(value) <= 64 and all(c in "abcdefghijklmnopqrstuvwxyz0123456789_-" for c in value)
    if not ok:
        raise fault("invalid")
    return value


def shape(obj, allowed: set, required: set = frozenset()) -> dict:
    if not isinstance(obj, dict) or not set(obj) <= allowed or not required <= set(obj):
        raise fault("invalid")
    return obj


def choice(value, options) -> str:
    if value not in options:
        raise fault("invalid")
    return value


def whole(value, low: int = 0, high: int = 2**32 - 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise fault("invalid")
    return value


def text_field(value) -> str:
    if not isinstance(value, str):
        raise fault("invalid")
    return value


def node_ref(value) -> dict:
    ref = shape(value, {"kind", "label"}, {"kind", "label"})
    return {"kind": choice(ref["kind"], KINDS), "label": text_field(ref["label"])}


def evidence(cmd: dict) -> dict:
    origin = choice(cmd.get("origin", "conversation"), ORIGINS)
    if origin == "user":
        raise fault("forbidden")
    return {
        "origin": origin,
        "reference": text_field(cmd.get("reference", "")),
        "confidence": whole(cmd.get("confidence", 800)),
    }


def query_of(raw) -> dict:
    allowed = {"text", "kinds", "limit", "depth", "household", "min_confidence", "reveal"}
    q = shape(raw, allowed)
    kinds = q.get("kinds", [])
    if not isinstance(kinds, list):
        raise fault("invalid")
    for flag in ("household", "reveal"):
        if not isinstance(q.get(flag, False), bool):
            raise fault("invalid")
    return {
        "text": text_field(q.get("text", "")),
        "kinds": [choice(k, KINDS) for k in kinds],
        "limit": whole(q.get("limit", 10), 0, 10**9),
        "depth": whole(q.get("depth", 1), 0, 10**9),
        "household": q.get("household", False),
        "min_confidence": whole(q.get("min_confidence", 0)),
        "reveal": q.get("reveal", False),
    }


class PyGraph:
    def __init__(self, clock=None):
        self.parts: dict[str, Part] = {}
        self.clock = clock or (lambda: int(time.time() * 1000))

    def handle(self, raw: str) -> str:
        try:
            if len(raw) > MAX_REQUEST:
                raise fault("too_large")
            try:
                cmd = json.loads(raw)
            except ValueError as error:
                raise fault("invalid") from error
            if not isinstance(cmd, dict):
                raise fault("invalid")
            data = self.execute(cmd)
            return json.dumps({"ok": True, "data": data}, ensure_ascii=False)
        except GraphFault as error:
            return json.dumps({"ok": False, "error": error.code})

    def own(self, who: str) -> Part:
        part = self.parts.get(who)
        if part is None:
            raise fault("not_found")
        if not part.consent:
            raise fault("forbidden")
        return part

    def totals(self) -> tuple[int, int]:
        return sum(len(p.nodes) for p in self.parts.values()), sum(len(p.edges) for p in self.parts.values())

    def visible(self, who: str, household: bool) -> list:
        me = self.own(who)
        out = [(me, "secret")]
        if household:
            for part in sorted(self.parts.values(), key=lambda p: p.owner):
                if part.owner != who and me.role == "family" and part.role == "family" and part.consent:
                    out.append((part, "family"))
            out.sort(key=lambda pair: pair[0].owner)
        return out

    def execute(self, cmd: dict):
        op = cmd.get("op")
        if op in UNSUPPORTED:
            raise fault("unsupported")
        now = self.clock()
        if op == "register":
            return self.register(shape(cmd, {"op", "id", "name", "role", "consent"}, {"op", "id", "name", "role"}))
        handler = getattr(self, "op_" + str(op), None)
        if handler is None:
            raise fault("invalid")
        return handler(cmd, now)

    def register(self, cmd: dict):
        who = person_id(cmd["id"])
        name = clean(text_field(cmd["name"]), 120)
        role = choice(cmd["role"], ("family", "guest"))
        consent = cmd.get("consent", True)
        if not isinstance(consent, bool):
            raise fault("invalid")
        existing = self.parts.get(who)
        if existing is not None:
            existing.name, existing.role, existing.consent = name, role, consent
        elif len(self.parts) >= 1000:
            raise fault("capacity")
        else:
            self.parts[who] = Part(who, name, role, consent)
        return {"registered": True}

    def op_remember(self, cmd: dict, now: int):
        shape(cmd, {"op", "as", "kind", "label", "detail", "level", "confidence", "origin", "reference"}, {"op", "as", "kind", "label"})
        who = person_id(cmd["as"])
        ev = evidence(cmd)
        detail = cmd.get("detail")
        if detail is not None:
            detail = text_field(detail)
        part = self.own(who)
        ident = writes.ensure_node(
            part, choice(cmd["kind"], KINDS), text_field(cmd["label"]), detail,
            choice(cmd.get("level", "private"), LEVELS), ev, now, self.totals()[0],
        )
        return {"id": ident}

    def op_relate(self, cmd: dict, now: int):
        shape(cmd, {"op", "as", "from", "relation", "to", "level", "confidence", "origin", "reference"}, {"op", "as", "from", "relation", "to"})
        who = person_id(cmd["as"])
        ev = evidence(cmd)
        link = {
            "from": node_ref(cmd["from"]),
            "relation": text_field(cmd["relation"]),
            "to": node_ref(cmd["to"]),
            "level": choice(cmd.get("level", "private"), LEVELS),
        }
        total_nodes, total_edges = self.totals()
        ident, change = writes.relate(self.own(who), total_nodes, total_edges, link, ev, now)
        return {"edge": ident, "change": change}

    def op_correct(self, cmd: dict, now: int):
        shape(cmd, {"op", "as", "correction"}, {"op", "as", "correction"})
        who = person_id(cmd["as"])
        raw = cmd["correction"]
        if not isinstance(raw, dict):
            raise fault("invalid")
        action = raw.get("action")
        part = self.own(who)
        total_nodes, total_edges = self.totals()
        if action == "assert":
            body = shape(raw, {"action", "from", "relation", "to", "level"}, {"action", "from", "relation", "to"})
            link = {
                "from": node_ref(body["from"]),
                "relation": text_field(body["relation"]),
                "to": node_ref(body["to"]),
                "level": choice(body.get("level", "private"), LEVELS),
            }
            ident, change = writes.relate(part, total_nodes, total_edges, link, writes.user_evidence(), now)
        elif action == "refute":
            body = shape(raw, {"action", "from", "relation", "to"}, {"action", "from", "relation", "to"})
            ident, change = writes.refute(part, total_nodes, node_ref(body["from"]), text_field(body["relation"]), node_ref(body["to"]), now)
        elif action == "remove":
            body = shape(raw, {"action", "node"}, {"action", "node"})
            ident, change = writes.remove(part, node_ref(body["node"]))
        else:
            raise fault("unsupported")
        return {"id": ident, "change": change}

    def op_search(self, cmd: dict, now: int):
        shape(cmd, {"op", "as", "query"}, {"op", "as", "query"})
        who = person_id(cmd["as"])
        query = query_of(cmd["query"])
        hits = reads.search(self.visible(who, query["household"]), who, query)
        own = [h["id"] for h in hits if h["owner"] == who]
        reads.touch(self.parts[who], own, now)
        return hits

    def op_neighbors(self, cmd: dict, now: int):
        shape(cmd, {"op", "as", "query"}, {"op", "as", "query"})
        who = person_id(cmd["as"])
        raw = shape(cmd["query"], {"node", "relation", "direction", "limit", "reveal"})
        relation = raw.get("relation")
        query = {
            "node": node_ref(raw["node"]) if raw.get("node") is not None else None,
            "relation": text_field(relation) if relation is not None else None,
            "direction": choice(raw.get("direction", "both"), ("out", "in", "both")),
            "limit": whole(raw.get("limit", 20), 0, 10**9),
            "reveal": raw.get("reveal", False) is True,
        }
        return reads.neighbors(self.own(who), query)

    def op_stats(self, cmd: dict, now: int):
        who = person_id(shape(cmd, {"op", "as"}, {"op", "as"})["as"])
        part = self.own(who)
        return {
            "nodes": len(part.nodes),
            "edges": len(part.edges),
            "pinned": sum(1 for n in part.nodes.values() if n["pinned"]),
            "by_kind": [{"kind": k, "nodes": sum(1 for n in part.nodes.values() if n["kind"] == k)} for k in KINDS],
            "observations": 0,
        }

    def op_export(self, cmd: dict, now: int):
        who = person_id(shape(cmd, {"op", "as"}, {"op", "as"})["as"])
        part = self.own(who)
        nodes = [{k: v for k, v in n.items() if k not in ("vec", "key", "uses", "last_used_ms")} for n in part.nodes.values()]
        return {"schema": 1, "owner": who, "name": part.name, "role": part.role, "nodes": nodes, "edges": list(part.edges.values()), "observations": {}}

    def op_erase(self, cmd: dict, now: int):
        body = shape(cmd, {"op", "as", "confirm"}, {"op", "as", "confirm"})
        who = person_id(body["as"])
        if body["confirm"] != "ERASE:" + who:
            raise fault("confirm")
        part = self.parts.pop(who, None)
        if part is None:
            raise fault("not_found")
        return {"receipt": {"nodes": len(part.nodes), "edges": len(part.edges), "observations": 0}, "file_removed": False}
