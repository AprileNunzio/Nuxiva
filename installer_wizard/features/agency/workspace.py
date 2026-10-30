import os
from pathlib import Path

from features.shares import archive

FILE_LIMIT = 2 * 1024 * 1024
FLAGS = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)


class WorkspaceError(RuntimeError):
    pass


def root() -> Path:
    return archive.ROOT / archive.FOLDERS["progetti"]


def folder(name: str) -> Path:
    base = root().resolve()
    target = (base / name).resolve()
    if target.parent != base:
        raise WorkspaceError("workspace outside the projects folder")
    return target


def write(name: str, relative: str, text: str) -> Path:
    base = folder(name)
    parts = [p for p in relative.split("/") if p]
    if not parts or any(p in (".", "..") or p.startswith(".") for p in parts):
        raise WorkspaceError("invalid file name")
    data = text.encode("utf-8")
    if len(data) > FILE_LIMIT:
        raise WorkspaceError("file too large")
    target = base.joinpath(*parts)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o775)
    if not target.parent.resolve().is_relative_to(base):
        raise WorkspaceError("path escapes the workspace")
    fd = os.open(target, FLAGS, 0o664)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
    return target


def read(name: str, relative: str, limit: int = 20000) -> str:
    target = folder(name).joinpath(*[p for p in relative.split("/") if p])
    if target.is_symlink() or not target.is_file() or not target.resolve().is_relative_to(folder(name)):
        return ""
    with target.open("r", encoding="utf-8", errors="replace") as handle:
        return handle.read(limit)
