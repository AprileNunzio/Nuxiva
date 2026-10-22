import re
import shutil
from pathlib import Path

from features.shares import archive

ROOT = archive.path("codice") / "progetti"
NAME = re.compile(r"^[a-z][a-z0-9-]{1,39}$")
SEGMENT = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
MAX_FILE = 512 * 1024
MAX_FILES = 400
MAX_TOTAL = 20 * 1024 * 1024
MAX_DEPTH = 8
READ_LIMIT = 64 * 1024
TREE_LIMIT = 200


class DevError(ValueError):
    pass


def slug(text: str) -> str:
    plain = re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")[:40]
    if not NAME.fullmatch(plain):
        raise DevError("nome progetto non valido: usa lettere, numeri e trattini, a partire da una lettera")
    return plain


def project_dir(name: str, must_exist: bool = True) -> Path:
    folder = ROOT / slug(name)
    if must_exist and not folder.is_dir():
        raise DevError(f"il progetto «{folder.name}» non esiste: crealo prima con dev_new")
    return folder


def safe_path(folder: Path, relative: str) -> Path:
    text = str(relative or "").replace("\\", "/").strip("/")
    parts = text.split("/") if text else []
    if not parts or len(parts) > MAX_DEPTH or any(p in (".", "..") or not SEGMENT.fullmatch(p) for p in parts):
        raise DevError("percorso non valido: serve un percorso relativo semplice dentro il progetto")
    target = folder.joinpath(*parts)
    probe = folder
    for part in parts[:-1]:
        probe = probe / part
        if probe.is_symlink():
            raise DevError("percorso non valido: collegamenti simbolici non ammessi")
    if target.is_symlink() or not target.resolve().is_relative_to(folder.resolve()):
        raise DevError("percorso fuori dal progetto")
    return target


def files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*") if p.is_file() and not p.is_symlink())


def usage(folder: Path) -> tuple[int, int]:
    rows = files(folder)
    return len(rows), sum(p.stat().st_size for p in rows)


def write(folder: Path, relative: str, content: str) -> Path:
    data = str(content).encode("utf-8")
    if len(data) > MAX_FILE:
        raise DevError(f"file troppo grande: massimo {MAX_FILE // 1024} KB")
    target = safe_path(folder, relative)
    count, total = usage(folder)
    existing = target.stat().st_size if target.is_file() else 0
    if (not target.exists() and count >= MAX_FILES) or total - existing + len(data) > MAX_TOTAL:
        raise DevError("il progetto ha raggiunto i limiti di file o di spazio")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target


def read(folder: Path, relative: str) -> str:
    target = safe_path(folder, relative)
    if not target.is_file():
        raise DevError("file non trovato nel progetto")
    return target.read_bytes()[:READ_LIMIT].decode("utf-8", errors="replace")


def tree(folder: Path) -> list[str]:
    rows = [f"{p.relative_to(folder).as_posix()} ({p.stat().st_size} B)" for p in files(folder)]
    return rows[:TREE_LIMIT] + ([f"…altri {len(rows) - TREE_LIMIT} file"] if len(rows) > TREE_LIMIT else [])


def names() -> list[str]:
    return sorted(p.name for p in ROOT.iterdir() if p.is_dir()) if ROOT.is_dir() else []


def remove(folder: Path) -> None:
    shutil.rmtree(folder)
