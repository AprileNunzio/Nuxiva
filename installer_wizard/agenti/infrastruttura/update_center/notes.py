from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from agenti.update_center import native

Git = Callable[..., Awaitable[Tuple[int, str]]]

DIR = "changelog"
LANGS = ("it", "en", "fr", "es")
MAX_FILE_BYTES = 16 * 1024
MAX_FILES = 60
MAX_TITLE = 140
MAX_ITEM = 320
MAX_ITEMS = 24
MAX_NAME = 96
DIFF_TIMEOUT = 60
READ_TIMEOUT = 15
_NAME = re.compile(r"^[0-9]{14}-[a-z0-9]+(?:-[a-z0-9]+)*\.json$")
_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_VERSION = re.compile(r"^[0-9]{1,4}\.[0-9]{1,4}\.[0-9]{1,4}(?:-[0-9A-Za-z.]{1,24})?$")
_INVISIBLE = ((0x200B, 0x200F), (0x202A, 0x202E), (0x2060, 0x2064), (0x2066, 0x2069), (0xFEFF, 0xFEFF),
              (0xFFF9, 0xFFFB))
_NOTE_KEYS = {"schema", "date", "title", "features", "fixes"}
_REQUIRED_KEYS = {"schema", "date", "title"}


class NoteError(ValueError):
    pass


def empty() -> Dict[str, Any]:
    return {"notes": [], "features": 0, "fixes": 0, "rejected": []}


def valid_name(name: str) -> bool:
    return isinstance(name, str) and len(name) <= MAX_NAME and bool(_NAME.fullmatch(name))


def _clean(text: str, limit: int) -> str:
    if any(unicodedata.category(c) == "Cc" or any(lo <= ord(c) <= hi for lo, hi in _INVISIBLE) for c in text):
        raise NoteError("text")
    trimmed = text.strip()
    if not trimmed or len(trimmed) > limit:
        raise NoteError("text")
    return trimmed


def _text(value: Dict[str, str], limit: int) -> Dict[str, str]:
    return {lang: _clean(value[lang], limit) for lang in LANGS}


def _items(value: List[Dict[str, str]]) -> List[Dict[str, str]]:
    if len(value) > MAX_ITEMS:
        raise NoteError("too_many")
    return [_text(item, MAX_ITEM) for item in value]


def _unique(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise NoteError("malformed")
        out[key] = value
    return out


def _valid_date(date: Any, stamp: str) -> bool:
    if not isinstance(date, str) or not _DATE.fullmatch(date):
        return False
    month, day = int(date[5:7]), int(date[8:10])
    return 1 <= month <= 12 and 1 <= day <= 31 and date.replace("-", "") == stamp[:8]


def _shape(value: Any) -> bool:
    return isinstance(value, dict) and set(value) == set(LANGS) and all(isinstance(value[k], str) for k in LANGS)


def _load(raw: str) -> Dict[str, Any]:
    try:
        data = json.loads(raw, object_pairs_hook=_unique, parse_constant=lambda _: None)
        json.dumps(data, ensure_ascii=False).encode("utf-8")
    except (ValueError, RecursionError, UnicodeEncodeError) as exc:
        raise NoteError("malformed") from exc
    if not isinstance(data, dict) or not _REQUIRED_KEYS <= set(data) <= _NOTE_KEYS:
        raise NoteError("malformed")
    schema = data["schema"]
    features, fixes = data.get("features", []), data.get("fixes", [])
    shaped = (type(schema) is int and 0 <= schema <= 255 and isinstance(data["date"], str) and _shape(data["title"])
              and isinstance(features, list) and isinstance(fixes, list) and all(map(_shape, features + fixes)))
    if not shaped:
        raise NoteError("malformed")
    return data


def py_parse(name: str, raw: str) -> Dict[str, Any]:
    if not valid_name(name):
        raise NoteError("name")
    if len(raw.encode("utf-8", "surrogatepass")) > MAX_FILE_BYTES:
        raise NoteError("too_large")
    data = _load(raw)
    if data["schema"] != 1:
        raise NoteError("schema")
    note_id = name[:-5]
    if not _valid_date(data["date"], note_id):
        raise NoteError("date")
    features, fixes = data.get("features", []), data.get("fixes", [])
    if not features and not fixes:
        raise NoteError("empty")
    return {"id": note_id, "date": data["date"], "title": _text(data["title"], MAX_TITLE),
            "features": _items(features), "fixes": _items(fixes)}


def py_digest(files: List[Tuple[str, str]]) -> Dict[str, Any]:
    out = empty()
    seen = set()
    for name, raw in files:
        try:
            note = py_parse(name, raw)
        except NoteError as exc:
            out["rejected"].append({"file": name if valid_name(name) else "", "reason": str(exc)})
            continue
        if note["id"] not in seen:
            seen.add(note["id"])
            out["notes"].append(note)
    out["notes"].sort(key=lambda n: n["id"], reverse=True)
    del out["notes"][MAX_FILES:]
    out["features"] = sum(len(n["features"]) for n in out["notes"])
    out["fixes"] = sum(len(n["fixes"]) for n in out["notes"])
    return out


def digest(files: List[Tuple[str, str]]) -> Dict[str, Any]:
    if native.RUST and hasattr(native._native, "update_release_notes"):
        return json.loads(native._native.update_release_notes(json.dumps(files)))
    return py_digest(files)


def added_files(name_only_z: str) -> List[str]:
    names = []
    for path in name_only_z.split("\0"):
        folder, _, name = path.strip().partition("/")
        if folder == DIR and valid_name(name):
            names.append(name)
    return sorted(set(names))[-MAX_FILES:]


async def collect(git: Git, base: Optional[str], target: Optional[str]) -> Dict[str, Any]:
    if not base or not target or base == target or not native.valid_rev(base) or not native.valid_rev(target):
        return empty()
    code, out = await git("diff", "--name-only", "-z", "--diff-filter=A", "--no-renames", "--end-of-options",
                          base, target, "--", f"{DIR}/", timeout=DIFF_TIMEOUT)
    if code != 0:
        return {**empty(), "error": "diff_unavailable"}
    files: List[Tuple[str, str]] = []
    for name in added_files(out):
        code, raw = await git("cat-file", "blob", f"{target}:{DIR}/{name}", timeout=READ_TIMEOUT)
        if code == 0:
            files.append((name, raw))
    report = digest(files)
    old, new = await _version(git, base), await _version(git, target)
    if new and new != old:
        report["version"] = new
    return report


async def _version(git: Git, rev: str) -> Optional[str]:
    code, raw = await git("cat-file", "blob", f"{rev}:VERSION", timeout=READ_TIMEOUT)
    value = raw.strip() if code == 0 else ""
    return value if _VERSION.fullmatch(value) else None


def compact(report: Optional[Dict[str, Any]], limit: int = 24) -> Optional[Dict[str, Any]]:
    if not report or not report.get("notes"):
        return None
    features = [item for note in report["notes"] for item in note.get("features", [])][:limit]
    fixes = [item for note in report["notes"] for item in note.get("fixes", [])][:limit]
    dates = sorted(str(note.get("date", "")) for note in report["notes"] if _DATE.fullmatch(str(note.get("date", ""))))
    version = report.get("version")
    return {"features": features, "fixes": fixes, "total_features": report.get("features", len(features)),
            "total_fixes": report.get("fixes", len(fixes)), "notes": len(report["notes"]),
            "date": dates[-1] if dates else None,
            "version": version if isinstance(version, str) and _VERSION.fullmatch(version) else None}
