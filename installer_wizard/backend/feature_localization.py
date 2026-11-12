"""Read presentation metadata from each scanned feature's own dictionaries."""
import json
import re
from pathlib import Path


def localize_feature(manifest: dict, language: str | None) -> dict:
    if not language or not re.fullmatch(r"[A-Za-z]{2,3}(?:[-_][A-Za-z0-9]{2,8})*", language):
        return manifest
    directory = Path(manifest["dir"]) / "language"
    candidates = [directory / f"{language}.json", directory / f"{language.split('-')[0].split('_')[0]}.json"]
    candidates.extend(sorted(directory.glob("*.json")))
    dictionary = {}
    for path in candidates:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            candidate = raw.get("dictionary", raw) if isinstance(raw, dict) else {}
            if isinstance(candidate, dict):
                dictionary = candidate
                break
        except (OSError, ValueError):
            continue
    result = dict(manifest)
    for key in ("name", "description"):
        if isinstance(dictionary.get(key), str):
            result[key] = dictionary[key]
    capabilities = dictionary.get("capabilities")
    if isinstance(capabilities, list) and all(isinstance(value, str) for value in capabilities):
        result["capabilities"] = capabilities
    labels = dictionary.get("settings", {})
    if isinstance(labels, dict):
        result["settings"] = [{**setting, "label": labels[setting["key"]] if isinstance(labels.get(setting["key"]), str) else setting.get("label", setting["key"])}
                              for setting in manifest.get("settings", [])]
    result["guide"] = _guide(dictionary.get("guide"))
    helps = dictionary.get("help")
    if isinstance(helps, dict):
        result["settings"] = [{**setting, "help": helps[setting["key"]][:400]} if isinstance(helps.get(setting["key"]), str) else setting
                              for setting in result.get("settings", [])]
    return result



def link_related(items: list[dict]) -> list[dict]:
    names = {item["id"]: str(item.get("name") or item["id"])[:80] for item in items if isinstance(item.get("id"), str)}
    for item in items:
        settings = item.get("settings") or []
        if any(isinstance(s, dict) and "see" in s for s in settings):
            item["settings"] = [_related(s, names, item["id"]) if isinstance(s, dict) else s for s in settings]
    return items


def _related(setting: dict, names: dict[str, str], own: str) -> dict:
    target = setting.get("see")
    clean = {k: v for k, v in setting.items() if k not in ("see", "see_name")}
    if not isinstance(target, str) or target == own or target not in names:
        return clean
    return {**clean, "see": target, "see_name": names[target]}

def _text(value, limit: int) -> str:
    return value[:limit] if isinstance(value, str) else ""


def _https(value) -> str:
    return value[:300] if isinstance(value, str) and value.startswith("https://") else ""


def _guide(raw) -> dict | None:
    if not isinstance(raw, dict):
        return None
    steps = [s[:500] for s in raw.get("steps", []) if isinstance(s, str)][:16] if isinstance(raw.get("steps"), list) else []
    links = []
    for link in raw.get("links", []) if isinstance(raw.get("links"), list) else []:
        if isinstance(link, dict) and isinstance(link.get("label"), str) and _https(link.get("url")):
            links.append({"label": link["label"][:80], "url": _https(link["url"])})
    items = []
    for item in raw.get("items", []) if isinstance(raw.get("items"), list) else []:
        if isinstance(item, dict) and _text(item.get("label"), 80):
            items.append({"label": _text(item["label"], 80), "detail": _text(item.get("detail"), 200), "url": _https(item.get("url"))})
    blocks = []
    for block in raw.get("copy", []) if isinstance(raw.get("copy"), list) else []:
        if isinstance(block, dict) and _text(block.get("text"), 4000):
            blocks.append({"label": _text(block.get("label"), 120), "text": _text(block["text"], 4000)})
    if not steps and not links:
        return None
    return {"title": str(raw.get("title", ""))[:80], "steps": steps, "links": links[:8], "note": str(raw.get("note", ""))[:600],
            "items_title": _text(raw.get("items_title"), 120), "items": items[:16], "copy": blocks[:3]}
