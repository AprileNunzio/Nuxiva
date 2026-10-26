import os
import re
import shutil
import tempfile
from pathlib import Path

from config import STATE_DIR

ROOT = STATE_DIR / "avatars"
ACTIVE_FILE = ROOT / "active.txt"
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,39}$")
FILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
MODELS = (".glb", ".fbx")
ALLOWED = {*MODELS, ".png", ".jpg", ".jpeg", ".webp"}
MAX_BYTES = 64 * 1024 * 1024
MAX_AVATARS = 32
CHUNK = 1024 * 1024


class AvatarError(ValueError):
    pass


def valid_name(name: str) -> str:
    name = str(name or "").strip()
    if not NAME_RE.match(name):
        raise AvatarError("Nome non valido: usa lettere, numeri, - e _")
    return name


def valid_file(filename: str) -> str:
    base = Path(str(filename or "").replace("\\", "/")).name.strip()
    if not FILE_RE.match(base) or ".." in base or Path(base).suffix.lower() not in ALLOWED:
        raise AvatarError("Formato non supportato: usa .glb, .fbx, .png, .jpg o .webp")
    return base


def _dir(name: str) -> Path:
    path = (ROOT / valid_name(name)).resolve()
    if path.parent != ROOT.resolve():
        raise AvatarError("Percorso non valido")
    return path


def active() -> str:
    try:
        name = ACTIVE_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""
    return name if NAME_RE.match(name) and _dir(name).is_dir() else ""


def model_file(name: str) -> str | None:
    folder = _dir(name)
    if not folder.is_dir():
        return None
    return next((f.name for f in sorted(folder.iterdir()) if f.is_file() and f.suffix.lower() in MODELS), None)


def active_model_url() -> str | None:
    name = active()
    model = model_file(name) if name else None
    return f"/api/avatars/serve/{name}/{model}" if model else None


def listing() -> dict:
    ROOT.mkdir(parents=True, exist_ok=True)
    items = []
    for folder in sorted(p for p in ROOT.iterdir() if p.is_dir() and NAME_RE.match(p.name)):
        files = [{"name": f.name, "size": f.stat().st_size} for f in sorted(folder.iterdir()) if f.is_file()]
        items.append({"name": folder.name, "files": files, "model": model_file(folder.name)})
    return {"avatars": items, "active": active(), "max_bytes": MAX_BYTES}


def set_active(name: str) -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    if not name:
        ACTIVE_FILE.unlink(missing_ok=True)
        return
    if not model_file(name):
        raise AvatarError("L'aspetto non contiene un modello 3D")
    tmp = ACTIVE_FILE.with_suffix(".tmp")
    tmp.write_text(valid_name(name), encoding="utf-8")
    os.replace(tmp, ACTIVE_FILE)


def save(name: str, filename: str, source) -> dict:
    ROOT.mkdir(parents=True, exist_ok=True)
    folder = _dir(name)
    target = folder / valid_file(filename)
    if not folder.exists() and sum(1 for p in ROOT.iterdir() if p.is_dir()) >= MAX_AVATARS:
        raise AvatarError("Troppi aspetti salvati")
    folder.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".upload-")
    written = 0
    try:
        with os.fdopen(fd, "wb") as out:
            while chunk := source.read(CHUNK):
                written += len(chunk)
                if written > MAX_BYTES:
                    raise AvatarError("File troppo grande")
                out.write(chunk)
        if written == 0:
            raise AvatarError("File vuoto")
        os.chmod(tmp, 0o640)
        os.replace(tmp, target)
    finally:
        Path(tmp).unlink(missing_ok=True)
    return {"avatar": folder.name, "file": target.name, "size": written}


def remove(name: str) -> None:
    folder = _dir(name)
    if active() == folder.name:
        ACTIVE_FILE.unlink(missing_ok=True)
    if folder.is_dir():
        shutil.rmtree(folder)


def resolve(name: str, filename: str) -> Path:
    folder = _dir(name)
    path = (folder / valid_file(filename)).resolve()
    if path.parent != folder or not path.is_file():
        raise FileNotFoundError(filename)
    return path
