import time
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from access import NO_CACHE

from agenti.capabilities import audit, tokens
from agenti.firewall.defense.guardian import guardian

router = APIRouter()
SCOPES = {"state": "firewall_defense", "incidents": "firewall_incidents"}
FIELDS = ("posture", "internet", "lan", "countries", "at", "engine")


def authenticate(request: Request, scope: str) -> dict:
    origin = request.headers.get("Origin")
    if origin and urlparse(origin).netloc != request.headers.get("Host", ""):
        raise HTTPException(403, "Origine non consentita")
    token = tokens.check(request.headers.get("Authorization", ""), request.client.host if request.client else "")
    if token is None:
        raise HTTPException(401, "token mancante o non valido", headers={"WWW-Authenticate": "Bearer"})
    allowed = token.get("allowed_tools")
    if not isinstance(allowed, list) or scope not in allowed:
        raise HTTPException(403, "il token non ha questo ambito")
    if not audit.allow(token["id"]):
        raise HTTPException(429, "troppe richieste: riprova tra un minuto", headers={"Retry-After": "60"})
    return token


def incident_view(row: dict) -> dict:
    return {k: row[k] for k in ("id", "origin", "country", "kinds", "stage", "level", "score", "alerts", "first_at", "last_at")} | {
        "source": row["src"], "targets": len(row["targets"])}


@router.get("/api/firewall/external/{name}")
async def external(name: str, request: Request):
    scope = SCOPES.get(name)
    if scope is None:
        raise HTTPException(404, "Risorsa sconosciuta")
    token = authenticate(request, scope)
    started = time.time()
    state = guardian.snapshot()
    body = ({k: state[k] for k in FIELDS if k in state} | {"defenses": len(state["responses"])}) if name == "state" else {
        "incidents": [incident_view(i) for i in state["incidents"][:50]]}
    audit.record(token, "firewall/external", scope, True, (time.time() - started) * 1000)
    return JSONResponse(body, headers=NO_CACHE)
