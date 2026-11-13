import json
import os
import re
import stat
from pathlib import Path

CATEGORIES = ("safety", "conversation", "personal", "home", "work", "media", "info", "system", "ambient")
MODES = ("collapse", "open")
LANGUAGES = ("it", "en", "fr", "es")
MEDIA = ("audio", "video")
MAX_FILE = 256 * 1024
MAX_TITLE = 60
MAX_SAY = 90
TITLE_KEY = "simple_title"
SAY_PREFIX = "say_"
_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{1,40}$")
_ICON = re.compile(r"^[a-z0-9_]{1,24}$")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _issue(field: str, code: str) -> dict:
    return {"field": field, "code": code, "severity": "error"}


def _readable(path: Path) -> str | None:
    try:
        info = os.lstat(path)
    except OSError:
        return None
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _text(value) -> str | None:
    return value if isinstance(value, str) else None


def check_manifest(manifest: dict) -> list[dict]:
    issues = []
    ident = _text(manifest.get("id"))
    if not ident or not _ID.match(ident):
        issues.append(_issue("id", "invalid"))
    if _text(manifest.get("category")) not in CATEGORIES:
        issues.append(_issue("category", "invalid"))
    if manifest.get("chrome") is not False:
        issues.append(_issue("chrome", "must_be_false"))
    for key in ("media", "exclusive"):
        if key in manifest and _text(manifest[key]) not in MEDIA:
            issues.append(_issue(key, "invalid"))
    simple = manifest.get("simple")
    if isinstance(simple, dict):
        if _text(simple.get("mode")) not in MODES:
            issues.append(_issue("simple.mode", "invalid"))
        icon = _text(simple.get("icon"))
        if not icon or not _ICON.match(icon):
            issues.append(_issue("simple.icon", "invalid"))
    else:
        issues.append(_issue("simple", "missing"))
    return issues


def _dictionary(path: Path) -> dict | None:
    raw = _readable(path)
    if raw is None:
        return None
    try:
        doc = json.loads(raw)
    except ValueError:
        return None
    words = doc.get("dictionary") if isinstance(doc, dict) else None
    return words if isinstance(words, dict) else None


def _clean(value) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not _CONTROL.search(value)


def _languages(directory: Path, issues: list[dict]) -> list[frozenset]:
    sets = []
    for lang in LANGUAGES:
        field = f"language/{lang}.json"
        words = _dictionary(directory / field)
        if words is None:
            issues.append(_issue(field, "unreadable"))
            continue
        title = words.get(TITLE_KEY)
        title = title.strip() if isinstance(title, str) else None
        if not title or len(title) > MAX_TITLE or _CONTROL.search(title):
            issues.append(_issue(field, "simple_title.invalid"))
        keys = set()
        for key, value in words.items():
            if not key.startswith(SAY_PREFIX):
                continue
            keys.add(key)
            if not _clean(value) or len(value) > MAX_SAY:
                issues.append(_issue(field, "say.invalid"))
        sets.append(frozenset(keys))
    return sets


def inspect(directory: Path) -> list[dict]:
    directory = Path(directory)
    raw = _readable(directory / "widget.json")
    try:
        manifest = json.loads(raw) if raw is not None else None
    except ValueError:
        manifest = None
    if manifest is None:
        return [_issue("widget.json", "unreadable")]
    issues = check_manifest(manifest if isinstance(manifest, dict) else {})
    sets = _languages(directory, issues)
    if any(a != b for a, b in zip(sets, sets[1:])):
        issues.append(_issue("language", "say_mismatch"))
    simple = manifest.get("simple") if isinstance(manifest, dict) else None
    if isinstance(simple, dict) and simple.get("mode") == "collapse":
        script = _readable(directory / "widget.js")
        if script is None or "headline" not in script:
            issues.append(_issue("widget.js", "headline.missing"))
        if len(sets) == len(LANGUAGES) and all(not s for s in sets):
            issues.append(_issue("language", "say_missing"))
    return sorted(issues, key=lambda i: (i["field"], i["code"]))


def inspect_best(directory: Path) -> list[dict]:
    try:
        import nuxiva_native
    except ImportError:
        return inspect(directory)
    native = getattr(nuxiva_native, "widget_inspect", None)
    if native is None:
        return inspect(directory)
    try:
        return json.loads(native(str(directory)))
    except (ValueError, TypeError):
        return inspect(directory)
