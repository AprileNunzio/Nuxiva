from fastapi import APIRouter, Depends, HTTPException, Request

from access import require_admin
from config import read_env, write_env
from feature_registry import registry
from features.home_assistant import address, home, probe
from features.home_assistant.reports import discovered
from state import store

admin_routes = APIRouter()
TOKEN_MAX = 2000


def current() -> dict:
    s = home.brain.settings()
    return {"urls": s["urls"], "token_set": bool(s["token"]), "verify_ssl": s["verify_ssl"], "enabled": s["enabled"],
            "status": home.brain.status, "error": home.brain.error, "active_url": home.brain.url if home.brain.online else "",
            "version": home.brain.ha_version, "name": home.brain.ha_name, "suggestions": discovered()}


def addresses(body: dict) -> list[str]:
    try:
        return address.parse(body.get("urls") if isinstance(body.get("urls"), list) else str(body.get("urls") or ""))
    except ValueError as exc:
        raise HTTPException(400, str(exc))


def secret(body: dict) -> str:
    token = str(body.get("token") or "").strip()
    if len(token) > TOKEN_MAX or any(ch.isspace() for ch in token):
        raise HTTPException(400, "Token non valido")
    return token


@admin_routes.get("/api/home/connection")
async def connection_get(_: str = Depends(require_admin)):
    return current()


@admin_routes.put("/api/home/connection")
async def connection_put(request: Request, user: str = Depends(require_admin)):
    body = await request.json()
    urls = addresses(body)
    token = secret(body)
    updates = {"HOME_ASSISTANT_URL": urls[0] if urls else "", "HOME_ASSISTANT_URLS": ",".join(urls[1:]),
               "HOME_ASSISTANT_VERIFY_SSL": "0" if body.get("verify_ssl") is False else "1"}
    if token:
        updates["HOME_ASSISTANT_TOKEN"] = token
    elif body.get("clear_token") is True:
        updates["HOME_ASSISTANT_TOKEN"] = ""
    if urls and (token or read_env().get("HOME_ASSISTANT_TOKEN")):
        updates["NUXIVA_HOME_ASSISTANT"] = "1"
    try:
        write_env(updates)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    registry.note_env_change(updates)
    store.event("INFO", f"Collegamento a Home Assistant aggiornato da {user}: {len(urls)} indirizzi", "home")
    return current()


@admin_routes.post("/api/home/connection/test")
async def connection_test(request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    s = home.brain.settings()
    urls = addresses(body) if body.get("urls") else s["urls"]
    if not urls:
        raise HTTPException(400, "Inserisci almeno un indirizzo")
    token = secret(body) or s["token"]
    verify = s["verify_ssl"] if body.get("verify_ssl") is None else bool(body.get("verify_ssl"))
    return {"results": await probe.probe_all(urls, token, verify)}
