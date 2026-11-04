import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse

import auth
import health
import machine
import setup_api
import updater
from access import NO_CACHE, require_admin, require_internal, session_user
from config import EDITABLE_KEYS, NUXIVA_DIR, NODE, env_get, is_secret, kiosk_log, read_env, write_env
from orchestrator import orch
from pages import page
from features.locale.api import page_language
from settings import apply_config
from snapshot import full_snapshot, sse
from state import INSTALL_LOG, store
from steps import STEP_BY_ID
from tasks import background, delayed

log = logging.getLogger("nuxiva.system_api")

public_routes = APIRouter()
admin_routes = APIRouter()
from features.system_logs.api import admin_routes as system_logs_routes
admin_routes.include_router(system_logs_routes)

LOG_SOURCES = {
    "install": "Installazione e step",
    "supervisor": "Supervisore (journal)",
    "core": "Nuxiva Core",
    "ollama": "Motore neurale",
    "kiosk": "Display kiosk",
    "rollback": "Rollback",
}
LOG_COMMANDS = {
    "install": lambda n: ("tail", "-n", n, str(INSTALL_LOG)),
    "supervisor": lambda n: ("journalctl", "-u", "nuxiva-supervisor", "-n", n, "--no-pager"),
    "core": lambda n: (("journalctl", "-u", "nuxiva-core", "-n", n, "--no-pager") if machine.core_runtime() == "native"
                       else ("docker", "logs", "--tail", n, "nuxiva-core")),
    "ollama": lambda n: ("journalctl", "-u", "ollama", "-n", n, "--no-pager"),
    "kiosk": lambda n: ("tail", "-n", n, str(kiosk_log())),
    "rollback": lambda n: ("tail", "-n", n, "/var/log/nuxiva/rollback.log"),
}
COMPONENT_RESTART = {
    "core": ["docker", "restart", "nuxiva-core"],
    "qdrant": ["docker", "restart", "nuxiva-qdrant"],
    "ollama": ["systemctl", "restart", "ollama"],
    "docker": ["systemctl", "restart", "docker"],
    "kiosk": ["systemctl", "restart", "getty@tty1"],
}


def _display_response(request: Request, res: Response) -> Response:
    has_display = bool(
        auth.verify(request.cookies.get(auth.DISPLAY_COOKIE))
        or auth.verify(request.cookies.get(auth.SESSION_COOKIE))
    )
    if not has_display:
        res.set_cookie(auth.DISPLAY_COOKIE, auth.issue("display"), max_age=auth.SESSION_TTL,
                       httponly=True, samesite="lax", secure=request.url.scheme == "https", path="/")
    return res


def _activation_completed() -> bool:
    try:
        if setup_api.done():
            import time
            from config import STATE_DIR
            store_path = STATE_DIR / "activation.json"
            if not store_path.exists():
                from features.activation.domain.journey import Journey, Stage
                from features.activation.infrastructure.journey_store import JourneyStore
                now = time.time()
                j = Journey(stage=Stage.DONE, created_at=now, updated_at=now)
                JourneyStore(store_path).save(j)
            return True
        from features.activation.infrastructure.journey_store import JourneyStore
        from features.activation.domain.journey import Stage
        from config import STATE_DIR
        store_path = STATE_DIR / "activation.json"
        if not store_path.exists():
            return False
        j = JourneyStore(store_path).load()
        return bool(j and j.stage == Stage.DONE)
    except Exception:
        return bool(setup_api.done())


@public_routes.get("/")
async def public_index(request: Request, node: str = ""):
    if store.phase != "INSTALLING" and setup_api.setup_required(request):
        return RedirectResponse("/setup", status_code=303)
    if node:
        from features.nodes.registry import registry
        if node in registry.data["nodes"]:
            NODE.set(node)
    page_name = "display/display.html" if _activation_completed() else "activation/activation.html"
    res = page(page_name, page_language(request, admin=False))
    return _display_response(request, res)


@public_routes.get("/screen")
async def public_screen(request: Request):
    if store.phase != "INSTALLING" and setup_api.setup_required(request):
        return RedirectResponse("/setup", status_code=303)
    res = page("screen/screen.html" if _activation_completed() else "monitor/monitor.html",
               page_language(request, admin=False))
    return _display_response(request, res)


@public_routes.get("/healthz")
@admin_routes.get("/healthz")
async def healthz():
    return {"ok": True, "phase": store.phase}


@public_routes.get("/api/state")
async def public_state():
    return JSONResponse(full_snapshot(admin=False), headers=NO_CACHE)


@public_routes.get("/api/system/identity")
@admin_routes.get("/api/system/identity")
async def system_identity():
    from config import env_get
    from identity import assistant_identity

    ident = assistant_identity()
    aliases_raw = env_get("NUXIVA_WAKE_PHONETIC_ALIASES", "").strip()
    aliases = [a.strip() for a in aliases_raw.split(",") if a.strip()] or [ident.wake_word]
    if ident.wake_word not in aliases:
        aliases.insert(0, ident.wake_word)
    return JSONResponse({
        "assistant_name": ident.name,
        "assistant_gender": ident.gender,
        "wake_word_primary": ident.wake_word,
        "wake_phrases": list(ident.wake_phrases),
        "wake_phonetic_aliases": aliases,
        "voice_id": env_get("NUXIVA_VOICE", "if_sara"),
        "locale": env_get("NUXIVA_UI_LANG", "it"),
        "is_custom_name": ident.is_custom,
    }, headers=NO_CACHE)


public_routes.add_api_route("/api/stream", sse(admin=False), methods=["GET"])

from pydantic import BaseModel
class HoloActionReq(BaseModel):
    express: str = None
    play: str = None
    stop: str = None
    shot: str = None
    seconds: float = None
    dance: bool = None
    sing: bool = None
    accessory: dict = None

@public_routes.post("/api/holo_action")
async def trigger_holo_action(req: HoloActionReq):
    store.holo_action = req.dict(exclude_none=True)
    store.version += 1
    return {"ok": True}


@admin_routes.get("/classic")
async def admin_index(request: Request):
    return RedirectResponse("/", status_code=308)


@admin_routes.post("/api/auth/login")
async def login(request: Request):
    if request.headers.get("X-Nuxiva-Request") != "1":
        raise HTTPException(403, "Richiesta non valida")
    body = await request.json()
    ip = request.client.host if request.client else "?"
    username = str(body.get("username", "")).strip()
    if auth.rate_limited(ip):
        raise HTTPException(429, "Troppi tentativi: riprova tra qualche minuto")
    ok = await asyncio.to_thread(auth.authenticate, username, str(body.get("password", "")), ip)
    if not ok:
        store.event("WARN", f"Accesso admin negato per '{username}' da {ip}", "auth")
        raise HTTPException(401, "Credenziali non valide o utente non autorizzato")
    store.event("INFO", f"Accesso admin: {username} da {ip}", "auth")
    resp = JSONResponse({"user": username})
    resp.set_cookie(auth.SESSION_COOKIE, auth.issue(username), max_age=auth.SESSION_TTL,
                    httponly=True, samesite="lax", secure=request.url.scheme == "https", path="/")
    return resp


@admin_routes.post("/api/auth/logout")
async def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(auth.SESSION_COOKIE, path="/", samesite="lax")
    return resp


@public_routes.get("/api/auth/me")
@admin_routes.get("/api/auth/me")
async def me(request: Request):
    user = session_user(request)
    if not user:
        raise HTTPException(401, "Accesso richiesto")
    return {"user": user}


@admin_routes.get("/api/state")
async def admin_state(_: str = Depends(require_admin)):
    return JSONResponse(full_snapshot(admin=True), headers=NO_CACHE)


@admin_routes.get("/api/stream")
async def admin_stream(request: Request, _: str = Depends(require_admin)):
    return await sse(admin=True)(request)


@admin_routes.get("/api/logs/{source}")
async def admin_logs(source: str, lines: int = 300, _: str = Depends(require_admin)):
    lines = max(20, min(lines, 3000))
    if source not in LOG_SOURCES:
        raise HTTPException(404, "Sorgente sconosciuta")
    _, out = await health.sh(*LOG_COMMANDS[source](str(lines)))
    return {"source": source, "text": out}


@admin_routes.post("/api/actions/{action}")
async def admin_action(action: str, request: Request, user: str = Depends(require_admin)):
    body = {}
    if request.headers.get("content-type", "").startswith("application/json"):
        body = await request.json()
    store.event("INFO", f"Azione admin '{action}' da {user}", "admin")

    if action == "repair":
        background(orch.converge(reason="Riparazione completa richiesta dall'amministratore"))
    elif action == "rerun-step":
        step_id = body.get("step")
        if step_id not in STEP_BY_ID:
            raise HTTPException(404, "Step sconosciuto")
        background(orch.converge([step_id], reason=f"Riesecuzione: {STEP_BY_ID[step_id].title}", force=True))
    elif action == "restart-component":
        comp = body.get("component")
        if comp not in COMPONENT_RESTART:
            raise HTTPException(404, "Componente sconosciuto")
        if comp == "kiosk":
            await health.sh("pkill", "-t", "tty1")
        command = ["systemctl", "restart", "nuxiva-core"] if comp == "core" and machine.core_runtime() == "native" else COMPONENT_RESTART[comp]
        code, out = await health.sh(*command, timeout=180)
        return {"ok": code == 0, "output": out[-500:]}
    elif action == "update-check":
        return await updater.check(allow_bad=True)
    elif action == "update-apply":
        info = await updater.check(allow_bad=True)
        target = info.get("target_rev") or info.get("remote_rev")
        local = info.get("local_rev")
        if not target or target == local:
            return {"ok": False, "message": "Nessun aggiornamento disponibile"}
        background(updater.apply("manuale", force=True))
        return {"ok": True, "message": "Aggiornamento avviato"}
    elif action == "update-clear-bad":
        updater.clear_bad_rev()
        return await updater.check(allow_bad=True)
    elif action == "reboot":
        background(delayed("systemctl", "reboot"))
    elif action in ("poweroff", "shutdown"):
        background(delayed("systemctl", "poweroff"))
    elif action == "restart-supervisor":
        background(delayed("systemctl", "restart", "nuxiva-supervisor"))
    else:
        raise HTTPException(404, "Azione sconosciuta")
    return {"ok": True}


@admin_routes.get("/api/background")
async def background_state(_: str = Depends(require_admin)):
    from background import queue
    return JSONResponse(queue.snapshot(), headers=NO_CACHE)


@admin_routes.post("/api/background/{action}")
async def background_action(action: str, step: str = "", _: str = Depends(require_admin)):
    from background import queue
    if action == "pause":
        queue.pause()
    elif action == "resume":
        queue.resume()
    elif action == "prioritize":
        if not queue.prioritize(step):
            raise HTTPException(404, "Installazione sconosciuta")
    else:
        raise HTTPException(404, "Azione sconosciuta")
    return queue.snapshot()


@admin_routes.post("/api/internal/{action}")
async def internal_action(action: str, request: Request):
    require_internal(request)
    store.event("INFO", f"Comando locale nuxivactl: {action}", "nuxivactl")
    if action == "update":
        info = await updater.check()
        if not info.get("available"):
            return {"ok": True, "message": f"Nuxiva è aggiornata ({(info.get('local_rev') or '?')[:7]}). "
                                           f"{info.get('last_result', '')}".strip()}
        background(updater.apply("richiesto da nuxivactl"))
        return {"ok": True, "message": f"Aggiornamento {info['local_rev'][:7]} → {(info.get('target_rev') or info['remote_rev'])[:7]} avviato: "
                                       "il supervisore si riavvierà e verificherà la nuova versione."}
    if action == "repair":
        background(orch.converge(reason="Riparazione richiesta da nuxivactl"))
        return {"ok": True, "message": "Verifica e riparazione di tutti i componenti avviata."}
    raise HTTPException(404, "Azione sconosciuta")


@admin_routes.get("/api/config")
async def get_config(_: str = Depends(require_admin)):
    env = read_env()
    items = []
    for key, label in EDITABLE_KEYS.items():
        value = env.get(key, "")
        secret = is_secret(key)
        items.append({"key": key, "label": label, "secret": secret,
                      "value": ("••••" + value[-4:]) if (secret and value) else value, "set": bool(value)})
    readonly = {k: ("••••" if v else "") if is_secret(k) else v for k, v in env.items() if k not in EDITABLE_KEYS}
    return {"editable": items, "system": readonly, "nuxiva_dir": str(NUXIVA_DIR)}


@admin_routes.put("/api/config")
async def put_config(request: Request, user: str = Depends(require_admin)):
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "Valore non valido")
    updates = {k: str(v).strip()[:4096] for k, v in body.items() if k in EDITABLE_KEYS and isinstance(v, (str, int, float, bool))}
    updates = {k: v for k, v in updates.items() if not (is_secret(k) and v.startswith("••••"))}
    if not updates:
        return {"ok": True, "changed": []}
    needs = await apply_config(updates, user)
    return {"ok": True, "changed": list(updates), "applying": needs}


from system_settings_api import (
    DEFAULT_BACKEND_SETTINGS,
    DEFAULT_DISPLAY_SETTINGS,
    SCREEN_KEYS,
    SCREEN_ROLES,
    SURFACE_DEFAULTS,
    _screen_roles,
    _surfaces,
    get_backend_settings,
    get_display_settings,
    safe_model,
    safe_ollama_url,
    save_backend_settings,
    save_display_settings,
    public_routes as settings_public_routes,
    admin_routes as settings_admin_routes,
)

public_routes.include_router(settings_public_routes)
admin_routes.include_router(settings_admin_routes)

store.display_settings = get_display_settings()

__all__ = [
    "DEFAULT_BACKEND_SETTINGS",
    "DEFAULT_DISPLAY_SETTINGS",
    "SCREEN_KEYS",
    "SCREEN_ROLES",
    "SURFACE_DEFAULTS",
    "_screen_roles",
    "_surfaces",
    "env_get",
    "get_backend_settings",
    "get_display_settings",
    "safe_model",
    "safe_ollama_url",
    "save_backend_settings",
    "save_display_settings",
    "write_env",
]


