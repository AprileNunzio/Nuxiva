import os
import stat
from pathlib import Path

from agenti import _manifest
from agenti._text import tokens

MANIFEST = "feature.json"
MAX_AGENTS = 200_000


def children(directory: Path) -> list[tuple[str, Path]]:
    try:
        entries = list(os.scandir(directory))
    except OSError:
        return []
    out = []
    for entry in entries:
        try:
            if _manifest.valid_folder(entry.name) and entry.is_dir(follow_symlinks=False):
                out.append((entry.name, Path(entry.path)))
        except OSError:
            continue
    return sorted(out)


def _stamp(path: Path) -> str | None:
    try:
        info = os.lstat(path)
    except OSError:
        return None
    if not stat.S_ISREG(info.st_mode):
        return None
    return f"{path}:{info.st_mtime_ns}:{info.st_size}"


def discover(roots: list[dict]) -> list[dict]:
    found: list[dict] = []
    for root in roots:
        base = Path(root["path"])
        if root["layout"] == "flat":
            groups = [(None, base)]
        else:
            groups = [(name, path) for name, path in children(base)]
        for category, directory in groups:
            for folder, path in children(directory):
                if len(found) >= MAX_AGENTS:
                    return found
                file = path / MANIFEST
                mark = _stamp(file)
                if mark is not None:
                    found.append({"path": file, "folder": folder, "category": category,
                                  "origin": root["origin"], "stamp": mark})
    return found


def signature(found: list[dict]) -> str:
    h = 0xCBF29CE484222325
    for item in found:
        for b in item["stamp"].encode("utf-8") + b"\0":
            h ^= b
            h = (h * 0x0100000001B3) & 0xFFFFFFFFFFFFFFFF
    return f"{h:016x}"


def _keywords(m: dict) -> list[str]:
    words: set[str] = set()
    fields = [m["id"].replace("_", " "), m["name"], m["description"], *m["capabilities"],
              *m["routing"]["nouns"], *m["routing"]["verbs"]]
    for field in fields:
        words.update(tokens(field))
    return sorted(words)


def _error(code: str, field: str = "") -> dict:
    return {"field": field, "code": code, "severity": "error"}


def build(found: list[dict], sig: str) -> dict:
    snap = {"signature": sig, "agents": {}, "rejected": [], "by_category": {}, "keywords": {}}
    for item in found:
        path = str(item["path"])
        try:
            data = item["path"].read_bytes()
        except OSError:
            snap["rejected"].append({"path": path, "issues": [_error("unreadable")]})
            continue
        if len(data) > _manifest.MAX_MANIFEST_BYTES:
            snap["rejected"].append({"path": path, "issues": [_error("too_large")]})
            continue
        try:
            raw = data.decode("utf-8")
        except UnicodeDecodeError:
            snap["rejected"].append({"path": path, "issues": [_error("invalid_utf8")]})
            continue
        report = _manifest.validate(raw, item["folder"], item["category"])
        m = report["manifest"]
        if m is None:
            if report["issues"]:
                snap["rejected"].append({"path": path, "issues": report["issues"]})
            continue
        if m["id"] in snap["agents"]:
            snap["rejected"].append({"path": path, "issues": [_error("id_duplicate", "id")]})
            continue
        snap["by_category"].setdefault(m["category"], []).append(m["id"])
        for word in _keywords(m):
            snap["keywords"].setdefault(word, []).append(m["id"])
        snap["agents"][m["id"]] = {"manifest": m, "dir": str(item["path"].parent),
                                   "origin": item["origin"], "issues": report["issues"]}
    return snap


def search(snap: dict, query: str, limit: int) -> list[tuple[str, int]]:
    hits: dict[str, int] = {}
    for word in tokens(query):
        for ident in snap["keywords"].get(word, ()):
            hits[ident] = hits.get(ident, 0) + 1
    ranked = sorted(hits.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked[:min(limit, 256)]
