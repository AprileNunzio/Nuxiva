from agenti.team.fascicoli import formato
from agenti.team.fascicoli.archivio import StoreError

MAX_LIMIT = 100
PREVIEW = 160


def _section(doc: dict, anchor: str) -> str:
    return next((s["body"] for s in doc["sections"] if s["anchor"] == anchor), "")


def _read(store, rel: str, name: str) -> dict | None:
    try:
        return store.read(rel, name)
    except (OSError, StoreError, ValueError):
        return None


def summary(store, rel: str) -> dict:
    request = _read(store, rel, "00-richiesta.md")
    outcome = _read(store, rel, "99-esito.md")
    check = _read(store, rel, "90-verifica.md")
    front = request["front"] if request else []
    meta = dict(front)
    return {
        "rel": rel,
        "id": rel.rsplit("/", 1)[1],
        "level": meta.get("livello", ""),
        "agents": meta.get("agenti", ""),
        "created": meta.get("creato", ""),
        "lang": meta.get("lingua", ""),
        "request": " ".join(_section(request, "request").split())[:PREVIEW] if request else "",
        "closed": outcome is not None,
        "checked": check is not None,
    }


def listing(store, limit: int) -> list[dict]:
    return [summary(store, rel) for rel in store.recent(max(1, min(limit, MAX_LIMIT)))]


def detail(store, rel: str) -> dict:
    report = store.verify(rel)
    if not report["files"] and not report["ok"]:
        raise StoreError("not_found")
    names = []
    for name in sorted(set(report.get("files", []))):
        if formato.kind_of_name(name):
            names.append(name)
    files = {}
    for name in names:
        doc = _read(store, rel, name)
        if doc is not None:
            files[name] = doc
    return {"rel": rel, "report": report, "files": files}

