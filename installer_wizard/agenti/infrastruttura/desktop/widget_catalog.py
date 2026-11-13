import json
import logging
from pathlib import Path

import native_module
from agenti import _widget_check

log = logging.getLogger("nuxiva.widgets")


def register_categories(found: dict[str, dict]) -> int:
    register = native_module.feature("display_register_widgets")
    if register is None:
        return 0
    try:
        return int(register(json.dumps({wid: m.get("category", "info") for wid, m in found.items()})))
    except ValueError as exc:
        log.error("Categorie dei widget non registrate nel motore nativo: %s", exc)
        return 0


def report_conformance(manifest: dict, folder: Path) -> list[dict]:
    if manifest.get("source") != "system":
        return []
    issues = _widget_check.inspect_best(folder)
    for issue in issues:
        log.warning("Widget %s non conforme: %s %s", manifest.get("id"), issue["field"], issue["code"])
    return issues


def item_fields(m: dict) -> dict:
    return {"size": m["size"], "name": m["name"], "icon": m["icon"], "rev": m["rev"], "css": m["has_css"],
            "chrome": m.get("chrome", True), "essential": m.get("essential", False), "urgent": m.get("urgent", False),
            "tone": m.get("tone", "cyan"), "overlay": m.get("overlay", False), "sticky": bool(m.get("sticky")),
            "immersive": bool(m.get("immersive")), "personal": m.get("personal", False),
            "sensitivity": m.get("sensitivity"), "guest_safe": bool(m.get("guest_safe")),
            "category": m.get("category", "info"), "media": m.get("media"), "exclusive": m.get("exclusive"),
            "simple": m.get("simple"), "screen_role": m.get("screen_role")}
