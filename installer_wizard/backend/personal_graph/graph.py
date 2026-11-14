import unicodedata

from personal_graph.primitives import embed, hex_digest, normalize, tokens

SELF_KEY = "@self"
KINDS = ("person", "place", "object", "habit", "preference", "event", "concept")
LEVELS = ("public", "family", "private", "secret")
ORIGINS = {"user": 1000, "conversation": 900, "document": 850, "sensor": 800, "inference": 600}
FUNCTIONAL = ("lives_in", "works_as", "works_at", "born_in", "spouse")
MAX_LABEL = 120
MAX_DETAIL = 1000
MAX_PROVENANCE = 8
MAX_NODES = 200_000
MAX_EDGES = 800_000
MAX_LIMIT = 50
MAX_DEPTH = 3
MAX_POSTING = 2048
MAX_EXPANSION = 256
DECAY = 500
MIN_SCORE = 120
GAIN = 150
INITIAL = 700


class GraphFault(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def fault(name: str) -> GraphFault:
    return GraphFault("knowledge." + name)


def clean(text: str, limit: int) -> str:
    if any(unicodedata.category(c) == "Cc" for c in text):
        raise fault("invalid")
    collapsed = " ".join(text.split())
    if not collapsed:
        raise fault("invalid")
    if len(collapsed) > limit:
        raise fault("too_large")
    return collapsed


def relation_name(text: str) -> str:
    ok = bool(text) and len(text) <= 48 and all(c in "abcdefghijklmnopqrstuvwxyz0123456789_" for c in text)
    if not ok:
        raise fault("invalid")
    return text


def key_of(kind: str, label: str) -> str:
    if label == SELF_KEY:
        if kind != "person":
            raise fault("invalid")
        return SELF_KEY
    label = clean(label, MAX_LABEL)
    key = normalize(label)
    if not key or label.startswith("@"):
        raise fault("invalid")
    return key


def node_id(kind: str, key: str) -> str:
    return hex_digest("nuxiva.knowledge.node.v1", kind, key)


def edge_id(src: str, relation: str, dst: str) -> str:
    return hex_digest("nuxiva.knowledge.edge.v1", src, relation, dst)


def level_rank(level: str) -> int:
    return LEVELS.index(level)


def evidence(ev: dict, now: int) -> tuple[int, dict]:
    reference = clean(ev["reference"], 128) if ev["reference"] else ""
    return min(ev["confidence"], ORIGINS[ev["origin"]]), {"origin": ev["origin"], "reference": reference, "at_ms": now}


def push_provenance(items: list, item: dict) -> None:
    items.append(item)
    while len(items) > MAX_PROVENANCE:
        victim = next((i for i, p in enumerate(items) if p["origin"] != "user"), 0)
        items.pop(victim)


class Part:
    def __init__(self, owner: str, name: str, role: str, consent: bool):
        self.owner = owner
        self.name = name
        self.role = role
        self.consent = consent
        self.nodes: dict[str, dict] = {}
        self.edges: dict[str, dict] = {}
        self.out: dict[str, list[str]] = {}
        self.inn: dict[str, list[str]] = {}
        self.tokens: dict[str, set[str]] = {}
        self.keys: dict[str, str] = {}
        self.blocked: set[str] = set()

    @staticmethod
    def searchable(node: dict) -> str:
        if node["detail"] is not None and node["level"] != "secret":
            return node["label"] + " " + node["detail"]
        return node["label"]

    def unindex(self, ident: str) -> None:
        node = self.nodes.get(ident)
        if node is None:
            return
        for token in tokens(self.searchable(node)):
            posting = self.tokens.get(token)
            if posting is not None:
                posting.discard(ident)
                if not posting:
                    del self.tokens[token]

    def refresh(self, ident: str) -> None:
        self.unindex(ident)
        node = self.nodes[ident]
        text = self.searchable(node)
        node["vec"] = embed(text)
        self.keys[node["kind"] + "\x00" + node["key"]] = ident
        for token in tokens(text):
            self.tokens.setdefault(token, set()).add(ident)

    def find(self, kind: str, key: str) -> str | None:
        return self.keys.get(kind + "\x00" + key)

    def link(self, ident: str, src: str, dst: str) -> None:
        self.out.setdefault(src, []).append(ident)
        self.inn.setdefault(dst, []).append(ident)

    def drop_edge(self, ident: str) -> None:
        edge = self.edges.pop(ident, None)
        if edge is None:
            return
        for table, node in ((self.out, edge["from"]), (self.inn, edge["to"])):
            items = table.get(node)
            if items is not None:
                items[:] = [e for e in items if e != ident]
                if not items:
                    del table[node]

    def drop_node(self, ident: str) -> None:
        incident = list(self.out.get(ident, [])) + list(self.inn.get(ident, []))
        for edge in incident:
            self.drop_edge(edge)
        self.unindex(ident)
        node = self.nodes.pop(ident, None)
        if node is not None:
            self.keys.pop(node["kind"] + "\x00" + node["key"], None)

    def edges_of(self, ident: str, outgoing: bool) -> list[dict]:
        table = self.out if outgoing else self.inn
        return [self.edges[e] for e in table.get(ident, []) if e in self.edges]
