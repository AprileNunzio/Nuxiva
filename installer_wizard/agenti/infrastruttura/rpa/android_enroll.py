import base64
import json

from access import require_admin
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from state import store

from agenti.nodes import trust
from agenti.nodes.enrollment import EnrollmentError, tokens
from agenti.rpa import android_release
from agenti.rpa.android_pairing import MAX_ACTIVE, PairingError, pairings
from agenti.secure import api as secure

admin_routes = APIRouter(tags=["RPA"])
public_routes = APIRouter(tags=["RPA"])
LINK_PREFIX = "nuxiva://enroll?d="
LIFETIME = 10 * 60


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
        if len(pairings.items) >= MAX_ACTIVE:
            raise EnrollmentError("enroll_too_many_tokens")
        token, expires = tokens.issue(LIFETIME)
        payload = {"server": origin, "token": token, "pin": pin, "expires": int(expires)}
        handle, code = pairings.create(token, payload, expires)
    except (EnrollmentError, PairingError) as exc:
        raise HTTPException(429, exc.code)
    store.event("INFO", f"Abbinamento monouso per l'app Android generato da {user}", "nodes")
    body = {"id": handle, "link": enrollment_link(payload), "code": code, "expires": int(expires),
            "server": origin, "fingerprint": pin[:16].upper(), "apk": found}
    return JSONResponse(body, headers={"Cache-Control": "no-store"})


@admin_routes.get("/api/android/enrollment/{handle}")
async def android_enrollment_state(handle: str, user: str = Depends(require_admin)):
    item = pairings.get(handle)
    if not item:
        state = "gone"
    elif not tokens.alive(item.token):
        pairings.revoke(handle)
        state = "enrolled"
    else:
        state = "code_used" if item.redeemed else "pending"
    return JSONResponse({"state": state}, headers={"Cache-Control": "no-store"})


@admin_routes.delete("/api/android/enrollment/{handle}")
async def android_enrollment_revoke(handle: str, user: str = Depends(require_admin)):
    token = pairings.revoke(handle)
    if token is None:
        raise HTTPException(404, "enroll_not_found")
    tokens.revoke(token)
    store.event("INFO", f"Abbinamento Android revocato da {user}", "nodes")
    return JSONResponse({"revoked": True}, headers={"Cache-Control": "no-store"})


@public_routes.post("/api/android/enrollment-code")
async def redeem_code(request: Request):
    if int(request.headers.get("content-length") or 0) > 256:
        raise HTTPException(413, "payload_too_large")
    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(400, "invalid_request")
    code = str(body.get("code") or "").strip() if isinstance(body, dict) else ""
    ip = request.client.host if request.client else "?"
    try:
        payload = pairings.redeem(code, ip)
    except PairingError as exc:
        store.event("WARN", f"Codice di abbinamento Android rifiutato da {ip}", "nodes")
        raise HTTPException(429 if exc.code == "rate_limited" else 403, exc.code)
    return JSONResponse(payload, headers={"Cache-Control": "no-store"})
