import base64
import json

from access import require_admin
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from state import store

from agenti.nodes import trust
from agenti.nodes.enrollment import EnrollmentError, tokens
from agenti.rpa import android_release
from agenti.secure import api as secure

admin_routes = APIRouter(tags=["RPA"])
LINK_PREFIX = "nuxiva://enroll?d="
LIFETIME = 15 * 60


def enrollment_link(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return LINK_PREFIX + base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


@admin_routes.get("/api/android/installer-info")
async def installer_info():
    found = await android_release.info()
    if not found:
        raise HTTPException(503, "android_apk_unavailable")
    return found


@admin_routes.post("/api/android/enrollment")
async def android_enrollment(request: Request, user: str = Depends(require_admin)):
    found = await android_release.info()
    if not found:
        raise HTTPException(503, "android_apk_unavailable")
    origin = trust.https_origin(request.url.hostname, secure._active["port"])
    if not origin:
        raise HTTPException(409, "enroll_https_unavailable")
    pin = trust.ca_pin()
    if not pin:
        raise HTTPException(409, "enroll_ca_missing")
    try:
        token, expires = tokens.issue(LIFETIME)
    except EnrollmentError as exc:
        raise HTTPException(429, exc.code)
    store.event("INFO", f"Iscrizione monouso per un nodo Android generata da {user}", "nodes")
    payload = {"server": origin, "token": token, "pin": pin, "expires": int(expires)}
    return JSONResponse({"link": enrollment_link(payload), "expires": int(expires), "apk": found},
                        headers={"Cache-Control": "no-store"})
