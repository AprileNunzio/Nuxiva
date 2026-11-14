ACTIONS = {
    "create_folder": ("path",),
    "create_file": ("path", "content", "overwrite"),
    "append_file": ("path", "content"),
    "read_file": ("path",),
    "list_folder": ("path",),
    "search_files": ("query", "folder"),
    "move_path": ("path", "destination"),
    "create_docx": ("path", "title", "paragraphs"),
    "append_docx": ("path", "destination", "paragraphs"),
    "open": ("path",),
    "open_app": ("name", "path"),
    "open_url": ("url",),
    "type_text": ("text",),
    "copy_text": ("text",),
    "run_powershell": ("command",),
    "window": ("op", "title"),
    "show_desktop": (),
    "press_keys": ("keys",),
}
MAX_ACTIONS = 4
MAX_TEXT = 20000
MAX_ITEMS = 200


def _scalar(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value[:MAX_TEXT]
    return None


def _clean_value(value):
    scalar = _scalar(value)
    if scalar is not None:
        return scalar
    if isinstance(value, list):
        items = [x[:MAX_TEXT] for x in value[:MAX_ITEMS] if isinstance(x, str)]
        return items
    return None


def sanitize(actions, allowed=None) -> list[dict]:
    names = ACTIONS if allowed is None else {k: v for k, v in ACTIONS.items() if k in allowed}
    if not isinstance(actions, list):
        return []
    clean = []
    for item in actions[:MAX_ACTIONS]:
        if not isinstance(item, dict) or item.get("type") not in names:
            continue
        entry = {"type": item["type"]}
        for field in names[item["type"]]:
            value = _clean_value(item.get(field))
            if value is not None:
                entry[field] = value
        clean.append(entry)
    return clean


def describe(allowed=None) -> str:
    names = ACTIONS if allowed is None else {k: v for k, v in ACTIONS.items() if k in allowed}
    return "; ".join(f"{k}({', '.join(v)})" if v else k for k, v in names.items())
