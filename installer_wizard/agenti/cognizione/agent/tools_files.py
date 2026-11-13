import fnmatch
import os
import shutil
import time
import zipfile
from pathlib import Path

from agenti.agent import fs_mcp
from agenti.agent.paths import FILES, TRASH, resolve, trusted
from agenti.agent import readers
from agenti.agent.readers import text_of
from agenti.agent.registry import tool
from agenti.shares import archive

TEXT_LIMIT = 8000
FIND_LIMIT = 100


def _size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _write_risk(args: dict) -> bool:
    return not trusted(resolve(args.get("path", "")))


@tool("list_dir", "elenca il contenuto di una cartella (vuoto = cartella di lavoro)", {"path": "cartella"}, consent=fs_mcp.consent("list_dir"))
async def list_dir(path: str = "") -> str:
    if fs_mcp.active():
        return await fs_mcp.call("list_dir", path=str(resolve(path or str(FILES))))
    p = resolve(path or str(FILES))
    if not p.is_dir():
        return f"{p} non è una cartella"
    items = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))[:200]
    rows = [f"{'📁' if i.is_dir() else '📄'} {i.name}{'' if i.is_dir() else ' (' + _size(i.stat().st_size) + ')'}" for i in items]
    return f"{p}:\n" + ("\n".join(rows) or "(vuota)")


@tool("read_file", "legge un file: testo, Word (.docx), Excel (.xlsx), PowerPoint (.pptx) o PDF", {"path": "file"}, consent=fs_mcp.consent("read_file"))
async def read_file(path: str) -> str:
    p = resolve(path)
    if fs_mcp.active():
        if p.suffix.lower() not in readers.DOCUMENTS:
            return await fs_mcp.call("read_file", path=str(p))
        await fs_mcp.call("file_info", path=str(p))
    if not p.is_file():
        return f"{p} non esiste o non è un file: cercalo prima con find_files"
    data = await text_of(p)
    return data[:TEXT_LIMIT] + ("\n…(troncato)" if len(data) > TEXT_LIMIT else "")


@tool("write_file", "crea o sovrascrive un file di testo (append=true per aggiungere in fondo)",
      {"path": "file", "content": "testo", "append": "true/false"}, confirm=_write_risk, consent=fs_mcp.consent("write_file"))
async def write_file(path: str, content: str, append: bool = False) -> str:
    p = resolve(path)
    if not p.exists() and p.parent.parent == archive.ROOT and not archive.DATED.match(p.name):
        p = archive.unique(p.parent, archive.dated(p.name))
    if fs_mcp.active():
        return await fs_mcp.call("write_file", path=str(p), content=str(content), append=str(append).lower() == "true")
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a" if str(append).lower() == "true" else "w", encoding="utf-8") as f:
        f.write(str(content))
    return f"scritto {p} ({_size(p.stat().st_size)})"


@tool("make_dir", "crea una cartella (anche annidata)", {"path": "cartella"}, confirm=_write_risk, consent=fs_mcp.consent("make_dir"))
async def make_dir(path: str) -> str:
    p = resolve(path)
    if fs_mcp.active():
        return await fs_mcp.call("make_dir", path=str(p))
    p.mkdir(parents=True, exist_ok=True)
    return f"cartella pronta: {p}"


@tool("copy", "copia un file o una cartella", {"src": "origine", "dst": "destinazione"},
      confirm=lambda a: not trusted(resolve(a.get("dst", ""))), consent=fs_mcp.consent("copy"))
async def copy(src: str, dst: str) -> str:
    s, d = resolve(src), resolve(dst)
    if fs_mcp.active():
        return await fs_mcp.call("copy", src=str(s), dst=str(d))
    if d.is_dir():
        d = d / s.name
    d.parent.mkdir(parents=True, exist_ok=True)
    if s.is_dir():
        shutil.copytree(s, d, dirs_exist_ok=True)
    else:
        shutil.copy2(s, d)
    return f"copiato in {d}"


@tool("move", "sposta o rinomina un file o una cartella", {"src": "origine", "dst": "destinazione"},
      confirm=lambda a: not (trusted(resolve(a.get("src", ""))) and trusted(resolve(a.get("dst", "")))),
      consent=fs_mcp.consent("move"))
async def move(src: str, dst: str) -> str:
    s, d = resolve(src), resolve(dst)
    if fs_mcp.active():
        return await fs_mcp.call("move", src=str(s), dst=str(d))
    if d.is_dir():
        d = d / s.name
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(s), str(d))
    return f"spostato in {d}"


@tool("delete", "sposta un file o una cartella nel cestino di Nuxiva (recuperabile)", {"path": "percorso"}, confirm=True, consent=fs_mcp.consent("delete"))
async def delete(path: str) -> str:
    p = resolve(path)
    if fs_mcp.active():
        return await fs_mcp.call("delete", path=str(p))
    if not p.exists():
        return f"{p} non esiste"
    dest = TRASH / time.strftime("%Y%m%d-%H%M%S") / p.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(p), str(dest))
    return f"spostato nel cestino: {dest}"


@tool("zip", "comprime un file o una cartella in un archivio .zip", {"path": "percorso", "dst": "archivio .zip (facoltativo)"})
async def zip_path(path: str, dst: str = "") -> str:
    p = resolve(path)
    out = resolve(dst) if dst else p.with_suffix(".zip") if p.is_file() else p.parent / f"{p.name}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in ([p] if p.is_file() else sorted(x for x in p.rglob("*") if x.is_file())):
            z.write(f, f.name if p.is_file() else f.relative_to(p.parent))
    return f"archivio creato: {out} ({_size(out.stat().st_size)})"


def matcher(pattern: str):
    wanted = str(pattern or "*").strip().lower()
    if not any(c in wanted for c in "*?["):
        wanted = f"*{wanted}*"
    return lambda name: fnmatch.fnmatch(name.lower(), wanted)


@tool("find_files", "cerca file e cartelle per nome, senza distinguere maiuscole (es. preventivo, *.stl) in tutta la "
      "cartella condivisa o in una cartella", {"pattern": "nome o schema", "root": "cartella (facoltativa)"},
      consent=fs_mcp.consent("find_files"))
async def find_files(pattern: str, root: str = "") -> str:
    base = resolve(root or str(archive.ROOT))
    if fs_mcp.active():
        return await fs_mcp.call("find_files", pattern=str(pattern or ""), root=str(base))
    hit, found = matcher(pattern), []
    for folder, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        found += [os.path.join(folder, n) for n in sorted(dirs + files) if hit(n)]
        if len(found) >= FIND_LIMIT:
            break
    return "\n".join(found[:FIND_LIMIT]) or f"nessun file trovato in {base}"


@tool("file_info", "dimensione e data di un file", {"path": "percorso"}, consent=fs_mcp.consent("file_info"))
async def file_info(path: str) -> str:
    p: Path = resolve(path)
    if fs_mcp.active():
        return await fs_mcp.call("file_info", path=str(p))
    st = p.stat()
    return f"{p}: {_size(st.st_size)}, modificato il {time.strftime('%d/%m/%Y %H:%M', time.localtime(st.st_mtime))}"
