import io
import json
import zipfile

from access import require_admin
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from state import store

from agenti.nodes import trust
from agenti.nodes.enrollment import EnrollmentError, tokens
from agenti.rpa import custom_installer, package, releases
from agenti.secure import api as secure

admin_routes = APIRouter(tags=["RPA"])
ENROLL_FILE = "enroll.json"


def _https_origin(request: Request) -> str:
    origin = trust.https_origin(request.url.hostname, secure._active["port"])
    if not origin:
        raise HTTPException(409, "enroll_https_unavailable")
    return origin


def _enrollment_payload(request: Request) -> bytes:
    origin = _https_origin(request)
    pin = trust.ca_pin()
    if not pin:
        raise HTTPException(409, "enroll_ca_missing")
    try:
        token, expires = tokens.issue()
    except EnrollmentError as exc:
        raise HTTPException(429, exc.code)
    return json.dumps({"server": origin, "token": token, "pin": pin, "expires": int(expires)}).encode()


@admin_routes.post("/api/rpa/enrolled-installer")
async def download_enrolled_installer(request: Request, user: str = Depends(require_admin)):
    info = await releases.installer_info()
    if not info:
        raise HTTPException(503, "windows_installer_unavailable")
    try:
        base = await custom_installer.base_installer(info)
    except custom_installer.InstallerUnavailable as exc:
        raise HTTPException(503, str(exc))
    extra = custom_installer.trailer(_enrollment_payload(request))
    store.event("INFO", f"Installer Windows personalizzato con token monouso generato da {user}", "nodes")
    return StreamingResponse(custom_installer.stream(base, extra), media_type="application/vnd.microsoft.portable-executable",
                             headers={"Content-Disposition": f"attachment; filename={releases.INSTALLER}",
                                      "Content-Length": str(base.stat().st_size + len(extra)),
                                      "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@admin_routes.post("/api/rpa/enrolled-client")
async def download_enrolled_client(request: Request, user: str = Depends(require_admin)):
    origin = _https_origin(request)
    pin = trust.ca_pin()
    if not pin:
        raise HTTPException(409, "enroll_ca_missing")
    try:
        token, expires = tokens.issue()
    except EnrollmentError as exc:
        raise HTTPException(429, exc.code)
    archive = package.generate_zip("")
    with zipfile.ZipFile(archive, "a", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(ENROLL_FILE, json.dumps({"server": origin, "token": token, "pin": pin, "expires": int(expires)}))
    archive.seek(0)
    store.event("INFO", f"Pacchetto Windows con token monouso generato da {user}", "nodes")
    return StreamingResponse(io.BytesIO(archive.read()), media_type="application/x-zip-compressed",
                             headers={"Content-Disposition": "attachment; filename=NUXIVA_Assistente_Windows.zip",
                                      "Cache-Control": "no-store"})
