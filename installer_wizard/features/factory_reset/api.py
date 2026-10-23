from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

import auth
from access import NO_CACHE, require_admin
from features.factory_reset import challenge, service

admin_routes = APIRouter(prefix="/api/factory-reset", tags=["Factory Reset"])


class Options(BaseModel):
    model_config = ConfigDict(extra="forbid")

    keep_backups: bool = False
    include_shares: bool = False

    def key(self) -> dict:
        return {"keep_backups": self.keep_backups, "include_shares": self.include_shares}


class ChallengeRequest(Options):
    password: str


class ExecuteRequest(Options):
    token: str
    phrase: str


def _client(request: Request) -> str:
    return request.client.host if request.client else ""


@admin_routes.get("/inventory")
async def inventory(keep_backups: bool = False, include_shares: bool = False, _: str = Depends(require_admin)):
    body = service.inventory(keep_backups, include_shares)
    body.update({"blockers": service.blockers(), "wait_seconds": int(challenge.MIN_WAIT), "ttl": int(challenge.TTL),
                 "last": service.last_report()})
    return JSONResponse(body, headers=NO_CACHE)


@admin_routes.get("/report")
async def report(_: str = Depends(require_admin)):
    data = service.last_report()
    if data is None:
        raise HTTPException(404, "report_missing")
    return JSONResponse(data, headers=NO_CACHE)


@admin_routes.post("/challenge")
async def open_challenge(body: ChallengeRequest, request: Request, user: str = Depends(require_admin)):
    ip = _client(request)
    if auth.rate_limited(ip):
        raise HTTPException(429, "too_many_attempts")
    if service.blockers():
        raise HTTPException(409, service.blockers()[0])
    if not auth.authenticate(user, body.password, ip):
        raise HTTPException(403, "invalid_credentials")
    return JSONResponse(challenge.challenges.issue(user, body.key()), headers=NO_CACHE)


@admin_routes.post("/execute", status_code=202)
async def execute(body: ExecuteRequest, user: str = Depends(require_admin)):
    try:
        challenge.challenges.redeem(body.token, user, body.phrase, body.key())
        result = service.start(user, body.keep_backups, body.include_shares)
    except challenge.ChallengeError as exc:
        raise HTTPException(exc.status, exc.code) from exc
    except service.ResetError as exc:
        raise HTTPException(exc.status, exc.code) from exc
    return JSONResponse(result, status_code=202, headers=NO_CACHE)
