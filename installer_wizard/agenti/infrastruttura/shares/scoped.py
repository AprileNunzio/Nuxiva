import errno
import logging
import os
import stat
import tempfile
from contextlib import ExitStack

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from access import require_admin
from agenti.authz.access_control import ROLE_PROFILES, account, allows
from agenti.authz.matrix_store import store as matrix
from agenti.shares import archive, policy

routes = APIRouter()
READ = {"x-nuxiva-capabilities": ["files.share.read"]}
WRITE = {"x-nuxiva-capabilities": ["files.share.write"]}
log = logging.getLogger("nuxiva.shares.scoped")
DOWNLOAD_RECHECK_BYTES = 1024 * 1024
WINDOWS_DEVICES = {"CON", "PRN", "AUX", "NUL", *(f"COM{index}" for index in range(1, 10)),
                   *(f"LPT{index}" for index in range(1, 10))}


def _matrix_allows(record: dict, *, write: bool) -> bool:
    if write and policy.read()["readonly"]:
        return False
    capability = "files.share.write" if write else "files.share.read"
    role = ROLE_PROFILES[record["role"]]
    verdict, _ = matrix.decide([capability], role, "strong", False, role == "owner")
    return verdict == "allow"


def _authorize(user: str, *, write: bool) -> dict:
    record = account(user)
    capability = "files.share.write" if write else "files.share.read"
    if not allows(record["role"], capability) or not _matrix_allows(record, write=write):
        raise HTTPException(403, "share_access_denied")
    return record


def _directory(stack: ExitStack, user: str, share: str, parts: tuple[str, ...] = (), *, write: bool = False) -> int:
    grant = _authorize(user, write=write).get("shares", {}).get(share)
    folder = archive.FOLDERS.get(share)
    if grant not in ({"write"} if write else {"read", "write"}) or folder is None:
        raise HTTPException(403, "share_access_denied")
    if os.open not in os.supports_dir_fd or not hasattr(os, "O_NOFOLLOW"):
        raise HTTPException(503, "share_scoped_io_unavailable")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    root = os.open(archive.ROOT, flags)
    stack.callback(os.close, root)
    directory = root
    for part in (folder, *parts):
        directory = os.open(part, flags, dir_fd=directory)
        stack.callback(os.close, directory)
    return directory


def _valid_part(part: str) -> bool:
    return bool(part and not part.startswith(".") and not any(char in part for char in "/\\\x00"))


def _valid_name(name: str) -> bool:
    return (_valid_part(name) and len(name.encode("utf-8")) <= 255 and name[-1] not in ". "
            and name.split(".", 1)[0].rstrip().upper() not in WINDOWS_DEVICES
            and not any(ord(char) < 32 or char in '<>:"|?*' for char in name))


def _path_parts(path: str, *, root_allowed: bool = False) -> tuple[str, ...]:
    if not path and root_allowed:
        return ()
    parts = tuple(path.split("/"))
    if len(parts) > 32 or not all(map(_valid_part, parts)):
        raise HTTPException(400, "share_invalid_path")
    return parts


@routes.get("/api/shares/scoped", openapi_extra=READ)
def list_assigned_shares(user: str = Depends(require_admin)):
    record = _authorize(user, write=False)
    grants = record.get("shares", {})
    can_write = allows(record["role"], "files.share.write") and _matrix_allows(record, write=True)
    return {"shares": [{"id": share, "name": name, "can_create": can_write and grants.get(share) == "write"}
                       for share, name in archive.FOLDERS.items()
                       if grants.get(share) in {"read", "write"}]}


@routes.get("/api/shares/scoped/{share}", openapi_extra=READ)
def list_share(share: str, subpath: str = Query(default="", max_length=4096), user: str = Depends(require_admin)):
    parts = _path_parts(subpath, root_allowed=True)
    try:
        with ExitStack() as stack:
            directory = _directory(stack, user, share, parts)
            with os.scandir(directory) as entries:
                items = [{"name": entry.name, "is_dir": entry.is_dir(follow_symlinks=False)}
                         for entry in entries if not entry.name.startswith(".") and not entry.is_symlink()]
    except OSError as exc:
        raise HTTPException(404, "share_unavailable") from exc
    return {"share": share, "path": subpath, "items": sorted(items, key=lambda item: item["name"].casefold())}


@routes.get("/api/shares/scoped/{share}/file", openapi_extra=READ)
def download(share: str, path: str = Query(max_length=4096), user: str = Depends(require_admin)):
    parts = _path_parts(path)
    try:
        with ExitStack() as stack:
            directory = _directory(stack, user, share, parts[:-1])
            descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            with os.fdopen(descriptor, "rb") as handle:
                metadata = os.fstat(handle.fileno())
                if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                    raise HTTPException(404, "share_unavailable")
                stream = os.fdopen(os.dup(handle.fileno()), "rb")
    except OSError as exc:
        raise HTTPException(404, "share_unavailable") from exc

    def chunks():
        with stream:
            remaining = metadata.st_size
            until_check = 0
            while remaining:
                if until_check == 0:
                    try:
                        grant = _authorize(user, write=False).get("shares", {}).get(share)
                    except HTTPException as exc:
                        log.warning("Download scoped interrotto per %s: %s", user, exc.detail)
                        return
                    if grant not in {"read", "write"}:
                        log.info("Download scoped interrotto per revoca a %s su %s", user, share)
                        return
                    until_check = DOWNLOAD_RECHECK_BYTES
                data = stream.read(min(64 * 1024, remaining, until_check))
                if not data:
                    return
                remaining -= len(data)
                until_check -= len(data)
                yield data
    return StreamingResponse(chunks(), media_type="application/octet-stream",
                             background=BackgroundTask(stream.close),
                             headers={"Cache-Control": "no-store", "Content-Disposition": "attachment",
                                      "Content-Length": str(metadata.st_size)})


@routes.post("/api/shares/scoped/{share}/folders", openapi_extra=WRITE, status_code=201)
def create_folder(share: str, name: str = Query(max_length=80), subpath: str = Query(default="", max_length=4096),
                  user: str = Depends(require_admin)):
    if not _valid_name(name):
        raise HTTPException(400, "share_invalid_path")
    parts = _path_parts(subpath, root_allowed=True)
    try:
        with ExitStack() as stack:
            directory = _directory(stack, user, share, parts, write=True)
            os.mkdir(name, mode=0o770, dir_fd=directory)
    except FileExistsError as exc:
        raise HTTPException(409, "share_folder_exists") from exc
    except OSError as exc:
        raise HTTPException(404, "share_unavailable") from exc
    return {"share": share, "name": name, "path": "/".join((*parts, name))}


@routes.put("/api/shares/scoped/{share}/file", openapi_extra=WRITE, status_code=201)
async def upload(share: str, request: Request, name: str = Query(max_length=180),
                 subpath: str = Query(default="", max_length=4096), user: str = Depends(require_admin)):
    if not _valid_name(name):
        raise HTTPException(400, "share_invalid_path")
    parts = _path_parts(subpath, root_allowed=True)
    limit = policy.upload_limit_mb() * 1024 * 1024
    written = 0
    try:
        with ExitStack() as stack:
            destination = _directory(stack, user, share, parts, write=True)
            staging = stack.enter_context(tempfile.NamedTemporaryFile(dir=archive.ROOT.parent))
            async for chunk in request.stream():
                written += len(chunk)
                if written > limit:
                    raise HTTPException(413, "share_upload_too_large")
                if chunk:
                    await run_in_threadpool(staging.write, chunk)
            await run_in_threadpool(staging.flush)
            await run_in_threadpool(os.fsync, staging.fileno())
            current = _directory(stack, user, share, parts, write=True)
            if not os.path.samestat(os.fstat(destination), os.fstat(current)):
                raise HTTPException(409, "share_directory_changed")
            os.link(staging.name, name, dst_dir_fd=current, follow_symlinks=False)
    except FileExistsError as exc:
        raise HTTPException(409, "share_file_exists") from exc
    except OSError as exc:
        raise HTTPException(503, "share_upload_unavailable") from exc
    return {"share": share, "name": name, "path": "/".join((*parts, name)), "size": written}


@routes.delete("/api/shares/scoped/{share}/entry", openapi_extra=WRITE)
def delete_entry(share: str, path: str = Query(max_length=4096), user: str = Depends(require_admin)):
    parts = _path_parts(path)
    name = parts[-1]
    try:
        with ExitStack() as stack:
            directory = _directory(stack, user, share, parts[:-1], write=True)
            metadata = os.stat(name, dir_fd=directory, follow_symlinks=False)
            if stat.S_ISDIR(metadata.st_mode):
                os.rmdir(name, dir_fd=directory)
            elif stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1:
                os.unlink(name, dir_fd=directory)
            else:
                raise HTTPException(404, "share_unavailable")
    except OSError as exc:
        if exc.errno in (errno.ENOTEMPTY, errno.EEXIST):
            raise HTTPException(409, "share_folder_not_empty") from exc
        raise HTTPException(404, "share_unavailable") from exc
    log.info("Scoped share entry deleted by %s on %s", user, share)
    return {"share": share, "path": path}
