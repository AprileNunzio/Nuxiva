from personal_graph.graph import (
    FUNCTIONAL,
    GAIN,
    INITIAL,
    LEVELS,
    MAX_DETAIL,
    MAX_EDGES,
    MAX_LABEL,
    MAX_NODES,
    SELF_KEY,
    Part,
    clean,
    edge_id,
    evidence,
    fault,
    key_of,
    level_rank,
    node_id,
    push_provenance,
    relation_name,
)
from personal_graph.primitives import noisy_or


def user_evidence() -> dict:
    return {"origin": "user", "reference": "correction", "confidence": 1000}


def ensure_node(part: Part, kind: str, label: str, detail: str | None, level: str, ev: dict, now: int, total: int) -> str:
    confidence, provenance = evidence(ev, now)
    key = key_of(kind, label)
    text = clean(detail, MAX_DETAIL) if detail is not None else None
    user = ev["origin"] == "user"
    if not user and (kind + "\x00" + key) in part.blocked:
        raise fault("forbidden")
    if level == "secret" and text is not None:
        raise fault("seal")
    existing = part.find(kind, key)
    if existing is not None:
        node = part.nodes[existing]
        node["confidence"] = noisy_or(node["confidence"], confidence)
        node["salience"] = noisy_or(node["salience"], GAIN)
        node["level"] = level if user else max(node["level"], level, key=level_rank)
        locked = node["pinned"] and not user
        node["pinned"] = node["pinned"] or user
        node["updated_ms"] = now
        push_provenance(node["provenance"], provenance)
        if text is not None and not locked:
            node["detail"] = text
        if node["level"] == "secret" and node["detail"] is not None:
            raise fault("seal")
        ident = existing
    else:
        if total >= MAX_NODES or len(part.nodes) >= MAX_NODES:
            raise fault("capacity")
        part.blocked.discard(kind + "\x00" + key)
        ident = node_id(kind, key)
        part.nodes[ident] = {
            "id": ident,
            "kind": kind,
            "key": key,
            "label": part.name if key == SELF_KEY else clean(label, MAX_LABEL),
            "detail": text,
            "level": level,
            "confidence": min(confidence, 1000),
            "salience": 1000 if user else INITIAL,
            "pinned": user,
            "created_ms": now,
            "updated_ms": now,
            "last_used_ms": now,
            "uses": 0,
            "provenance": [provenance],
        }
    part.refresh(ident)
    return ident


def rival_gate(part: Part, src: str, relation: str, dst: str, user: bool, confidence: int, now: int):
    if relation not in FUNCTIONAL:
        return ("go", False)
    rivals = [
        e["id"]
        for e in part.edges_of(src, True)
        if e["relation"] == relation and e["to"] != dst and e["status"] == "active"
    ]
    if not user and rivals:
        strongest = max((part.edges[r]["pinned"], part.edges[r]["confidence"]) for r in rivals)
        if strongest[0]:
            return ("stop", "blocked")
        if confidence < strongest[1]:
            return ("stop", "contested")
    superseded = False
    for ident in rivals:
        edge = part.edges[ident]
        edge["status"] = "superseded"
        edge["pinned"] = False
        edge["updated_ms"] = now
        superseded = True
    return ("go", superseded)


def apply_edge(part: Part, ident: str, ends: tuple, relation: str, level: str, ev: tuple, user: bool, now: int) -> str:
    confidence, provenance = ev
    edge = part.edges.get(ident)
    if edge is not None:
        reactivated = edge["status"] != "active"
        edge["status"] = "active"
        edge["confidence"] = confidence if (user or reactivated) else noisy_or(edge["confidence"], confidence)
        edge["salience"] = noisy_or(edge["salience"], GAIN)
        edge["level"] = level if user else max(edge["level"], level, key=level_rank)
        edge["pinned"] = edge["pinned"] or user
        edge["updated_ms"] = now
        push_provenance(edge["provenance"], provenance)
        return "created" if reactivated else "reinforced"
    part.edges[ident] = {
        "id": ident,
        "from": ends[0],
        "to": ends[1],
        "relation": relation,
        "level": level,
        "status": "active",
        "confidence": confidence,
        "salience": 1000 if user else INITIAL,
        "pinned": user,
        "created_ms": now,
        "updated_ms": now,
        "last_used_ms": now,
        "provenance": [provenance],
    }
    part.link(ident, ends[0], ends[1])
    return "created"


def relate(part: Part, total_nodes: int, total_edges: int, link: dict, ev: dict, now: int) -> tuple[str, str]:
    relation_name(link["relation"])
    confidence, provenance = evidence(ev, now)
    user = ev["origin"] == "user"
    src_ref, dst_ref, level = link["from"], link["to"], link["level"]
    src = ensure_node(part, src_ref["kind"], src_ref["label"], None, level, ev, now, total_nodes)
    dst_key = key_of(dst_ref["kind"], dst_ref["label"])
    dst = node_id(dst_ref["kind"], dst_key)
    ident = edge_id(src, link["relation"], dst)
    current = part.edges[ident]["status"] if ident in part.edges else None
    if current == "refuted" and not user:
        return ident, "blocked"
    gate = rival_gate(part, src, link["relation"], dst, user, confidence, now)
    if gate[0] == "stop":
        return ident, gate[1]
    if current is None and total_edges >= MAX_EDGES:
        raise fault("capacity")
    dst = ensure_node(part, dst_ref["kind"], dst_ref["label"], None, level, ev, now, total_nodes)
    floor = max((level, part.nodes[src]["level"], part.nodes[dst]["level"]), key=level_rank)
    change = apply_edge(part, ident, (src, dst), link["relation"], floor, (confidence, provenance), user, now)
    return ident, "superseded" if gate[1] and change == "created" else change


def refute(part: Part, total_nodes: int, src_ref: dict, relation: str, dst_ref: dict, now: int) -> tuple[str, str]:
    relation_name(relation)
    ev = user_evidence()
    src = ensure_node(part, src_ref["kind"], src_ref["label"], None, "private", ev, now, total_nodes)
    dst = ensure_node(part, dst_ref["kind"], dst_ref["label"], None, "private", ev, now, total_nodes)
    ident = edge_id(src, relation, dst)
    _, provenance = evidence(ev, now)
    edge = part.edges.get(ident)
    if edge is not None:
        edge.update(status="refuted", confidence=0, pinned=True, updated_ms=now)
        push_provenance(edge["provenance"], provenance)
    else:
        part.edges[ident] = {
            "id": ident,
            "from": src,
            "to": dst,
            "relation": relation,
            "level": "private",
            "status": "refuted",
            "confidence": 0,
            "salience": 1000,
            "pinned": True,
            "created_ms": now,
            "updated_ms": now,
            "last_used_ms": now,
            "provenance": [provenance],
        }
        part.link(ident, src, dst)
    return ident, "superseded"


def remove(part: Part, ref: dict) -> tuple[str, str]:
    key = key_of(ref["kind"], ref["label"])
    ident = part.find(ref["kind"], key)
    if ident is None:
        raise fault("not_found")
    node = part.nodes[ident]
    if node["key"] == SELF_KEY:
        raise fault("forbidden")
    if len(part.blocked) >= 10_000:
        raise fault("capacity")
    part.blocked.add(node["kind"] + "\x00" + node["key"])
    part.drop_node(ident)
    return ident, "superseded"


__all__ = ["LEVELS", "ensure_node", "relate", "refute", "remove", "user_evidence"]
