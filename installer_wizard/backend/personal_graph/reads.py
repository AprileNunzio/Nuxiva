from personal_graph.graph import (
    MAX_DEPTH,
    MAX_EXPANSION,
    MAX_LIMIT,
    MAX_POSTING,
    DECAY,
    GAIN,
    MIN_SCORE,
    SELF_KEY,
    Part,
    fault,
    key_of,
    level_rank,
    relation_name,
)
from personal_graph.primitives import cosine_permille, embed, noisy_or, scale, tokens


def hit(part: Part, node: dict, score: int, via, reveal: bool) -> dict:
    hidden = node["level"] == "secret" and not reveal
    return {
        "owner": part.owner,
        "id": node["id"],
        "kind": node["kind"],
        "label": node["label"],
        "detail": None if hidden else node["detail"],
        "level": node["level"],
        "confidence": node["confidence"],
        "salience": node["salience"],
        "pinned": node["pinned"],
        "score": score,
        "via": via,
    }


def seeds(part: Part, ceiling: str, qvec: tuple, qtokens: set, query: dict) -> list[tuple[int, str]]:
    population = max(len(part.nodes), 1)
    overlap: dict[str, int] = {}
    total = 0
    for token in sorted(qtokens):
        postings = part.tokens.get(token, set())
        df = len(postings)
        if df > MAX_POSTING:
            continue
        idf = max(1000 - df * 1000 // population, 100)
        total += idf
        for ident in postings:
            overlap[ident] = overlap.get(ident, 0) + idf
    out: list[tuple[int, str]] = []
    for node in part.nodes.values():
        if (
            level_rank(node["level"]) > level_rank(ceiling)
            or node["confidence"] < query["min_confidence"]
            or (query["kinds"] and node["kind"] not in query["kinds"])
        ):
            continue
        semantic = cosine_permille(qvec, node["vec"])
        lexical = overlap.get(node["id"], 0) * 1000 // total if total else 0
        base = (semantic * 6 + lexical * 4) // 10
        factor = 400 + scale(node["confidence"], node["salience"]) * 6 // 10
        score = scale(base, factor)
        if score >= MIN_SCORE:
            out.append((score, node["id"]))
    out.sort(key=lambda s: (-s[0], s[1]))
    return out[: max(query["limit"] * 2, 8)]


def expand(part: Part, ceiling: str, seed: str, score: int, depth: int, found: dict) -> None:
    queue = [(seed, score, 0)]
    seen = {seed}
    budget = MAX_EXPANSION
    cursor = 0
    while cursor < len(queue):
        ident, current, hop = queue[cursor]
        cursor += 1
        if hop >= depth or budget == 0:
            continue
        for outgoing in (True, False):
            for edge in part.edges_of(ident, outgoing):
                other = edge["to"] if outgoing else edge["from"]
                node = part.nodes.get(other)
                if node is None:
                    continue
                if (
                    edge["status"] != "active"
                    or level_rank(edge["level"]) > level_rank(ceiling)
                    or level_rank(node["level"]) > level_rank(ceiling)
                    or other in seen
                ):
                    continue
                seen.add(other)
                budget = max(budget - 1, 0)
                nxt = scale(scale(current, DECAY), edge["confidence"])
                slot = found.get(other, (0, None))
                if nxt > slot[0]:
                    found[other] = (nxt, edge["relation"])
                elif other not in found:
                    found[other] = slot
                queue.append((other, nxt, hop + 1))


def search(parts: list, me: str, query: dict) -> list[dict]:
    if not 1 <= query["limit"] <= MAX_LIMIT or query["depth"] > MAX_DEPTH:
        raise fault("invalid")
    text = query["text"]
    if any(ord(c) < 32 or ord(c) == 127 or 0x80 <= ord(c) < 0xA0 for c in text) or len(text) > 400:
        raise fault("invalid")
    qvec = embed(text)
    qtokens = set(tokens(text))
    best: dict[tuple[str, str], dict] = {}
    for part, ceiling in parts:
        reveal = query["reveal"] and part.owner == me
        top = seeds(part, ceiling, qvec, qtokens, query)
        found: dict[str, tuple] = {ident: (score, None) for score, ident in top}
        for score, ident in top:
            expand(part, ceiling, ident, score, query["depth"], found)
        for ident, (score, via) in found.items():
            node = part.nodes.get(ident)
            if (
                node is None
                or level_rank(node["level"]) > level_rank(ceiling)
                or node["confidence"] < query["min_confidence"]
                or (query["kinds"] and node["kind"] not in query["kinds"])
            ):
                continue
            best[(part.owner, ident)] = hit(part, node, score, via, reveal)
    hits = sorted(best.values(), key=lambda h: (-h["score"], h["owner"], h["id"]))
    return hits[: query["limit"]]


def touch(part: Part, ids: list[str], now: int) -> None:
    for ident in ids:
        node = part.nodes.get(ident)
        if node is not None:
            node["uses"] += 1
            node["last_used_ms"] = now
            node["salience"] = noisy_or(node["salience"], GAIN)


def neighbors(part: Part, query: dict) -> list[dict]:
    if not 1 <= query["limit"] <= MAX_LIMIT:
        raise fault("invalid")
    node = query["node"] or {"kind": "person", "label": SELF_KEY}
    if query["relation"] is not None:
        relation_name(query["relation"])
    ident = part.find(node["kind"], key_of(node["kind"], node["label"]))
    if ident is None:
        raise fault("not_found")
    out = []
    for outgoing in (True, False):
        if (query["direction"] == "out" and not outgoing) or (query["direction"] == "in" and outgoing):
            continue
        for edge in part.edges_of(ident, outgoing):
            other = edge["to"] if outgoing else edge["from"]
            target = part.nodes.get(other)
            if target is None or (query["relation"] is not None and query["relation"] != edge["relation"]):
                continue
            out.append(
                {
                    "edge": edge["id"],
                    "relation": edge["relation"],
                    "outgoing": outgoing,
                    "status": edge["status"],
                    "confidence": edge["confidence"],
                    "pinned": edge["pinned"],
                    "node": hit(part, target, edge["confidence"], None, query["reveal"]),
                }
            )
    out.sort(key=lambda r: (-r["confidence"], r["relation"], r["edge"]))
    return out[: query["limit"]]
