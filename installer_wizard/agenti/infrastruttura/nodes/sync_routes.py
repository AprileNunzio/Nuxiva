import base64
import hashlib
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from agenti.nodes.registry import registry
from agenti.shares import archive as shares_archive

public_routes = APIRouter()
MAX_SYNC_FILE_SIZE = 50 * 1024 * 1024  # 50 MB per file limit
SKIP_NAMES = {".git", ".DS_Store", "desktop.ini", "Thumbs.db"}


def _auth_node(request: Request) -> dict:
    node_id = request.headers.get("x-nuxiva-node", "")
    auth = request.headers.get("authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    try:
        return registry.authenticate(node_id, token)
    except PermissionError as exc:
        raise HTTPException(401, str(exc)) from exc


def _safe_target(person_dir: Path, rel_path: str) -> Path:
    clean = str(rel_path or "").strip().replace("\\", "/").lstrip("/")
    if not clean or ".." in clean.split("/"):
        raise HTTPException(400, "sync_invalid_path")
    target = (person_dir / clean).resolve()
    if not str(target).startswith(str(person_dir.resolve())):
        raise HTTPException(400, "sync_path_traversal")
    return target


def _file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def _scan_person_files(person_dir: Path) -> list[dict]:
    items = []
    if not person_dir.is_dir():
        return items
    for root, dirs, files in os.walk(person_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIP_NAMES]
        for name in files:
            if name.startswith(".") or name in SKIP_NAMES or name == shares_archive.README:
                continue
            file_path = Path(root) / name
            try:
                stat = file_path.stat()
                rel = str(file_path.relative_to(person_dir)).replace("\\", "/")
                items.append({
                    "path": rel,
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                    "sha256": _file_sha256(file_path),
                })
            except OSError:
                continue
    return items


@public_routes.post("/api/nodes/sync/status")
async def sync_status(request: Request):
    node = _auth_node(request)
    person_slug = node.get("person_slug") or "default"
    person_dir = shares_archive.person_folder(person_slug)
    server_host = request.url.hostname or "NUXIVA"

    body = {}
    try:
        raw = await request.body()
        if raw:
            import json
            body = json.loads(raw)
    except Exception:
        pass

    server_files = _scan_person_files(person_dir)
    server_by_path = {f["path"]: f for f in server_files}
    client_files = body.get("files") or []
    client_by_path = {f["path"]: f for f in client_files if isinstance(f, dict) and "path" in f}

    to_pull = []
    to_push = []

    for rel, s_file in server_by_path.items():
        c_file = client_by_path.get(rel)
        if not c_file:
            to_pull.append(rel)
        elif s_file["sha256"] != c_file.get("sha256"):
            if s_file["mtime"] > c_file.get("mtime", 0):
                to_pull.append(rel)
            else:
                to_push.append(rel)

    for rel, c_file in client_by_path.items():
        if rel not in server_by_path:
            to_push.append(rel)

    return {
        "person_slug": person_slug,
        "smb_path": f"\\\\{server_host}\\condivisa\\persone\\{person_slug}",
        "server_files": server_files,
        "to_pull": to_pull,
        "to_push": to_push,
    }


@public_routes.post("/api/nodes/sync/pull")
async def sync_pull(request: Request):
    node = _auth_node(request)
    person_slug = node.get("person_slug") or "default"
    person_dir = shares_archive.person_folder(person_slug)

    import json
    raw = await request.body()
    try:
        body = json.loads(raw) if raw else {}
    except Exception as exc:
        raise HTTPException(400, "sync_invalid_body") from exc

    rel_path = str(body.get("path") or "").strip()
    target = _safe_target(person_dir, rel_path)
    if not target.is_file():
        raise HTTPException(404, "sync_file_not_found")
    if target.stat().st_size > MAX_SYNC_FILE_SIZE:
        raise HTTPException(413, "sync_file_too_large")

    data = target.read_bytes()
    return {
        "path": rel_path,
        "content_b64": base64.b64encode(data).decode("ascii"),
        "mtime": target.stat().st_mtime,
    }


@public_routes.post("/api/nodes/sync/push")
async def sync_push(request: Request):
    node = _auth_node(request)
    person_slug = node.get("person_slug") or "default"
    person_dir = shares_archive.person_folder(person_slug)

    import json
    raw = await request.body()
    try:
        body = json.loads(raw) if raw else {}
    except Exception as exc:
        raise HTTPException(400, "sync_invalid_body") from exc

    rel_path = str(body.get("path") or "").strip()
    target = _safe_target(person_dir, rel_path)
    b64_content = str(body.get("content_b64") or "")
    try:
        data = base64.b64decode(b64_content)
    except Exception as exc:
        raise HTTPException(400, "sync_invalid_base64") from exc

    if len(data) > MAX_SYNC_FILE_SIZE:
        raise HTTPException(413, "sync_file_too_large")

    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp_sync")
    tmp.write_bytes(data)
    os.replace(tmp, target)

    mtime = body.get("mtime")
    if isinstance(mtime, (int, float)) and mtime > 0:
        try:
            os.utime(target, (mtime, mtime))
        except OSError:
            pass

    return {"ok": True, "path": rel_path}


@public_routes.post("/api/nodes/sync/delete")
async def sync_delete(request: Request):
    node = _auth_node(request)
    person_slug = node.get("person_slug") or "default"
    person_dir = shares_archive.person_folder(person_slug)

    import json
    raw = await request.body()
    try:
        body = json.loads(raw) if raw else {}
    except Exception as exc:
        raise HTTPException(400, "sync_invalid_body") from exc

    rel_path = str(body.get("path") or "").strip()
    target = _safe_target(person_dir, rel_path)
    if target.is_file():
        try:
            target.unlink()
        except OSError as exc:
            raise HTTPException(500, f"sync_delete_failed: {exc}") from exc

    return {"ok": True, "path": rel_path}
