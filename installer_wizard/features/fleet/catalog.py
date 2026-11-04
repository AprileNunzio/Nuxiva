from features.fleet.model import MAX_LIMIT
from features.team.stopwords import clean_tokens

SUGGESTIONS = 8


def _registry() -> dict:
    from features.agent import registry
    return registry.TOOLS


def _widgets() -> dict:
    from features.desktop.desk import desk
    desk.scan()
    return desk.widgets


def has_tool(name: str) -> bool:
    return name in _registry()


def has_widget(widget_id: str) -> bool:
    return widget_id in _widgets()


def tools(query: str = "", limit: int = 50) -> list[dict]:
    needle = query.strip().lower()
    rows = [{"id": name, "name": name, "description": str(row.get("description", ""))[:200]} for name, row in _registry().items()]
    if needle:
        rows = [row for row in rows if needle in row["id"].lower() or needle in row["description"].lower()]
    return sorted(rows, key=lambda row: row["id"])[: max(1, min(MAX_LIMIT, limit))]


def widgets(query: str = "", limit: int = 50) -> list[dict]:
    needle = query.strip().lower()
    rows = [{"id": wid, "name": str(manifest.get("name", wid)), "description": str(manifest.get("description", ""))[:200]}
            for wid, manifest in _widgets().items()]
    if needle:
        rows = [row for row in rows if needle in row["id"].lower() or needle in row["name"].lower() or needle in row["description"].lower()]
    return sorted(rows, key=lambda row: row["id"])[: max(1, min(MAX_LIMIT, limit))]


def _score(purpose: set[str], row: dict) -> int:
    return len(purpose & clean_tokens(f"{row['id']} {row['name']} {row['description']}".replace("_", " ")))


def suggest(purpose: str) -> dict:
    wanted = clean_tokens(purpose)
    if not wanted:
        return {"tools": [], "widgets": []}
    result = {}
    for kind, rows in (("tools", tools("", MAX_LIMIT * 5)), ("widgets", widgets("", MAX_LIMIT * 5))):
        ranked = sorted(((_score(wanted, row), row["id"]) for row in rows), key=lambda pair: (-pair[0], pair[1]))
        result[kind] = [name for score, name in ranked if score > 0][:SUGGESTIONS]
    return result
