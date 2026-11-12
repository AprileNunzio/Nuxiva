import io
import json
import zipfile

from access import require_admin
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from state import store

from features.nodes import trust
from features.nodes.enrollment import EnrollmentError, tokens
from features.rpa import package
from features.secure import api as secure

admin_routes = APIRouter(tags=["RPA"])
ENROLL_FILE = "enroll.json"


def _https_origin(request: Request) -> str:
    origin = trust.https_origin(request.url.hostname, secure._active["port"])
    if not origin:
        raise HTTPException(409, "enroll_https_unavailable")
    return origin


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
