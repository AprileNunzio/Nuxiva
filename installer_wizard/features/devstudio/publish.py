import json
import shutil
import time
from pathlib import Path

from features.actions.common import my_ip
from features.devstudio.workspace import DevError, files, project_dir
from features.shares import archive

STATIC = {".html", ".css", ".js", ".json", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".ico", ".txt", ".woff2", ".webmanifest"}
HOMES = ("", "dist", "build", "public")


def site_root(folder: Path) -> Path:
    for home in HOMES:
        candidate = folder / home if home else folder
        if (candidate / "index.html").is_file():
            return candidate
    raise DevError("nessun index.html: per React esegui prima la build e poi pubblica la cartella dist")


def publish(name: str) -> str:
    folder = project_dir(name)
    root = site_root(folder)
    target = archive.folder("siti") / folder.name
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    copied = 0
    for source in files(root):
        if source.suffix.lower() not in STATIC or "node_modules" in source.parts:
            continue
        destination = target / source.relative_to(root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied += 1
    if not copied:
        raise DevError("nessun file pubblicabile")
    (target / "sito.json").write_text(json.dumps({"title": folder.name, "request": "devstudio", "created_at": time.time()}), encoding="utf-8")
    return f"http://{my_ip()}/siti/{folder.name}/"
