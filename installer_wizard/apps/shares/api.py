from pathlib import Path
import re

from fastapi import APIRouter, Depends, HTTPException, Request

from access import require_admin
from config import DEMO, env_get
from features.actions.common import SMB_CONF, my_ip
from state import store

public_routes = APIRouter()
admin_routes = APIRouter()
USER = "nuxiva-share"


@admin_routes.get("/api/shares")
async def overview(_: str = Depends(require_admin)):
    from health import sh
    try:
        conf = SMB_CONF.read_text(errors="ignore")
    except OSError:
        conf = ""
    shares = []
    for name, body in re.findall(r"(?ms)^\[([^\]]+)\]\s*\n(.*?)(?=^\[|\Z)", conf):
        if name.lower() in ("global", "printers", "print$", "homes"):
            continue
        path = re.search(r"(?m)^\s*path\s*=\s*(.+)$", body)
        guest = re.search(r"(?mi)^\s*guest ok\s*=\s*yes", body)
        shares.append({"name": name, "path": path.group(1).strip() if path else "", "guest": bool(guest)})
    active = "demo" if DEMO else (await sh("systemctl", "is-active", "smbd", timeout=5))[1].strip()
    ip = my_ip()
    from features.shares import archive
    try:
        archive.ensure()
    except OSError as exc:
        store.event("WARN", f"Cartelle condivise non create: {exc}", "shares")
    return {"active": active, "ip": ip, "windows": f"\\\\{ip}", "unc": archive.unc(ip), "user": USER,
            "password": env_get("NUXIVA_SMB_PASSWORD", ""), "shares": shares, "folders": archive.overview(),
            "root": str(archive.ROOT)}


@admin_routes.get("/api/shares/files")
async def list_files(subpath: str = "", _: str = Depends(require_admin)):
    from features.shares import archive
    archive.ensure()
    base = archive.ROOT.resolve()
    target = (base / subpath.strip("/\\")).resolve()
    if not target.is_relative_to(base):
        raise HTTPException(400, "Percorso non consentito")
    if not target.exists() or not target.is_dir():
        raise HTTPException(404, "Cartella non trovata")
    items = []
    for entry in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        if entry.name.startswith("."):
            continue
        try:
            stat = entry.stat()
            size = stat.st_size if entry.is_file() else 0
            mtime = int(stat.st_mtime)
        except OSError:
            size, mtime = 0, 0
        ext = entry.suffix.lower() if entry.is_file() else ""
        items.append({
            "name": entry.name,
            "is_dir": entry.is_dir(),
            "path": str(entry.relative_to(base)).replace("\\", "/"),
            "size": size,
            "mtime": mtime,
            "ext": ext,
        })
    ip = my_ip()
    rel_str = str(target.relative_to(base)).replace("/", "\\")
    unc = f"\\\\{ip}\\{archive.SHARE}\\{rel_str}" if rel_str != "." else f"\\\\{ip}\\{archive.SHARE}"
    return {"folder": target.name if target != base else archive.SHARE, "path": str(target.relative_to(base)).replace("\\", "/") if target != base else "", "unc": unc, "items": items}


@admin_routes.get("/api/shares/file")
async def get_file_content(path: str = "", _: str = Depends(require_admin)):
    from fastapi.responses import FileResponse
    from features.shares import archive
    base = archive.ROOT.resolve()
    target = (base / path.strip("/\\")).resolve()
    if not target.is_relative_to(base):
        raise HTTPException(400, "Percorso non consentito")
    if not target.exists() or not target.is_file():
        raise HTTPException(404, "File non trovato")
    ext = target.suffix.lower()
    media_types = {
        ".txt": "text/plain; charset=utf-8",
        ".md": "text/markdown; charset=utf-8",
        ".json": "application/json",
        ".py": "text/plain; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".ts": "text/plain; charset=utf-8",
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".stl": "model/stl",
        ".obj": "model/obj",
        ".glb": "model/gltf-binary",
        ".gltf": "model/gltf+json",
    }
    media_type = media_types.get(ext, "application/octet-stream")
    return FileResponse(target, media_type=media_type, filename=target.name)


@admin_routes.post("/api/shares/create_folder")
async def create_folder(payload: dict, _: str = Depends(require_admin)):
    from features.shares import archive
    base = archive.ROOT.resolve()
    parent = (base / str(payload.get("parent", "")).strip("/\\")).resolve()
    if not parent.is_relative_to(base):
        raise HTTPException(400, "Percorso non consentito")
    name = archive.clean(str(payload.get("name", "")).strip(), fallback="nuova-cartella")
    new_dir = parent / name
    new_dir.mkdir(parents=True, exist_ok=True)
    return {"ok": True, "name": name, "path": str(new_dir.relative_to(base)).replace("\\", "/")}


MAX_UPLOAD_SHARE = 1000 * 1024 * 1024  # 1 GB


@admin_routes.put("/api/shares/upload")
async def upload_share_file(request: Request, subpath: str = "", name: str = "", _: str = Depends(require_admin)):
    from features.shares import archive
    base = archive.ROOT.resolve()
    target_dir = (base / subpath.strip("/\\")).resolve()
    if not target_dir.is_relative_to(base):
        raise HTTPException(400, "Percorso non consentito")
    target_dir.mkdir(parents=True, exist_ok=True)
    raw_name = Path(name).name.strip() or "file"
    suffix = Path(raw_name).suffix
    stem = Path(raw_name).stem
    clean_stem = archive.clean(stem, fallback="file")
    final_name = f"{clean_stem}{suffix}" if suffix else clean_stem
    out_file = target_dir / final_name
    written = 0
    try:
        with open(out_file, "wb") as handle:
            async for chunk in request.stream():
                written += len(chunk)
                if written > MAX_UPLOAD_SHARE:
                    raise HTTPException(413, "File troppo grande")
                handle.write(chunk)
    except HTTPException:
        out_file.unlink(missing_ok=True)
        raise
    except OSError as exc:
        out_file.unlink(missing_ok=True)
        raise HTTPException(500, f"Errore scrittura: {exc}")
    return {"ok": True, "name": final_name, "path": str(out_file.relative_to(base)).replace("\\", "/"), "size": written}


