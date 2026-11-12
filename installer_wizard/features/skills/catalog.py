import inspect
import logging

from features.skills.library import library

log = logging.getLogger("nuxiva.skills.catalog")


def _skills() -> list[dict]:
    rows = []
    for item in library.listing()["skills"]:
        stats = item["stats"]
        rows.append({"key": f"skill:{item['key']}", "ref": item["key"], "kind": "skill", "name": item["name"],
                     "description": item["description"], "group": item["category_label"], "source": item["source"],
                     "manageable": True, "editable": item["source"] != "system", "enabled": stats.get("enabled", True),
                     "uses": stats.get("uses", 0), "fails": stats.get("fails", 0), "examples": item["examples"],
                     "patterns": item["patterns"], "created_at": item.get("created_at")})
    return rows


def _tools() -> list[dict]:
    try:
        from features.agent import registry
        registry.refresh()
        tools = list(registry.TOOLS.values())
    except Exception as exc:
        log.warning("Strumenti dell'agente non leggibili: %s", exc)
        return []
    rows = []
    for tool in sorted(tools, key=lambda t: t["name"]):
        try:
            enabled = bool(registry.enabled(tool["name"]))
        except Exception:
            enabled = True
        rows.append({"key": f"tool:{tool['name']}", "ref": tool["name"], "kind": "tool", "name": tool["name"],
                     "description": str(tool.get("description", ""))[:300], "group": tool.get("agent") or "agent",
                     "source": "system", "manageable": False, "editable": False, "enabled": enabled,
                     "confirm": bool(tool.get("confirm")), "arguments": list((tool.get("args") or {}).keys())})
    return rows


def _connectors() -> list[dict]:
    from features.chat.assistant import CLAIMS, CONNECTORS
    CLAIMS.claiming("")
    declared = set((CLAIMS.recognizers or {}).keys())
    rows = []
    for name, module in sorted(CONNECTORS.items()):
        doc = ""
        try:
            import importlib
            doc = inspect.getdoc(importlib.import_module(module)) or ""
        except Exception as exc:
            log.info("Connettore %s non leggibile: %s", name, exc)
        rows.append({"key": f"connector:{name}", "ref": name, "kind": "connector", "name": name,
                     "description": doc.split("\n")[0][:300], "group": module.split(".")[1] if "." in module else module,
                     "source": "system", "manageable": False, "editable": False, "enabled": True,
                     "declares_requests": name in declared})
    return rows


def scan() -> dict:
    skills, tools, connectors = _skills(), _tools(), _connectors()
    return {"entries": [*skills, *tools, *connectors],
            "counts": {"skill": len(skills), "tool": len(tools), "connector": len(connectors)},
            "categories": library.listing()["categories"], "errors": library.errors,
            "generate": library.may_generate()}
