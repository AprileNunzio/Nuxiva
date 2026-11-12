import time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from access import NO_CACHE, is_local, require_admin, require_display, require_internal, session_user
from config import env_get
from features.authz.access_control import account, allows
from features.desktop.camera_probe import probe_camera
from features.desktop.camera_sessions import (
    SESSION_HEADER, TTL_SECONDS, camera_owner, camera_sessions, require_camera_enabled,
)
from features.desktop.desk import FILES, desk
from features.desktop.sources import PROVIDERS, SOURCES
from features.music import music
from features.nodes.display_link import display_node
from state import store

public_routes = APIRouter()
admin_routes = APIRouter()
public_routes.add_api_route("/api/display/remote-media/camera/probe", probe_camera, methods=["POST"])


@public_routes.get("/api/display/remote-media")
async def remote_media(request: Request):
    user = session_user(request) if request.url.scheme == "https" else None
    authorized = request.url.scheme == "https" and bool(user or display_node(request))
    camera = authorized and env_get("NUXIVA_REMOTE_CAMERA_PREVIEW", "0") == "1"
    return JSONResponse({
        "camera_preview": camera,
        "camera_probe": bool(camera and user and env_get("NUXIVA_REMOTE_CAMERA_PROBE", "0") == "1"
                             and allows(account(user)["role"], "api.admin")),
        "microphone": authorized and env_get("NUXIVA_REMOTE_MIC_INPUT", "0") == "1",
    }, headers=NO_CACHE)


@public_routes.post("/api/display/remote-media/camera")
async def create_remote_camera(request: Request):
    owner = camera_owner(request)
    require_camera_enabled()
    return JSONResponse({"token": camera_sessions.issue(owner), "expires_in": TTL_SECONDS},
                        status_code=201, headers=NO_CACHE)


@public_routes.put("/api/display/remote-media/camera")
async def renew_remote_camera(request: Request):
    owner = camera_owner(request)
    require_camera_enabled()
    if not camera_sessions.update(request.headers.get(SESSION_HEADER, ""), owner):
        raise HTTPException(404, "camera.session.expired")
    return JSONResponse({"expires_in": TTL_SECONDS}, headers=NO_CACHE)


@public_routes.delete("/api/display/remote-media/camera")
async def revoke_remote_camera(request: Request):
    owner = camera_owner(request)
    camera_sessions.update(request.headers.get(SESSION_HEADER, ""), owner, revoke=True)
    return JSONResponse({"ok": True}, headers=NO_CACHE)

desk.register_source("now_playing", music.watcher.current)
for _name, _fn in SOURCES.items():
    desk.register_source(_name, _fn)
for _name, _fn in PROVIDERS.items():
    desk.register_provider(_name, _fn)


def _alert(body: dict, red: bool = True) -> dict:
    kind = str(body.get("kind") or "generic")[:30]
    key = f"alarm:{kind}:{str(body.get('room') or '')[:40]}"
    from features.redalert.service import redalert
    if body.get("clear"):
        redalert.stop()
        desk.hide(key=key)
        store.event("INFO", f"Allarme {kind} rientrato", "alarm")
        return {"ok": True, "cleared": key}
    data = {"kind": kind, "room": str(body.get("room") or "")[:60], "title": str(body.get("title") or "")[:80],
            "message": str(body.get("message") or "")[:300], "at": time.time(), "test": body.get("test") is True}
    where = ("in " + data["room"]) if data["room"] else ""
    data["speak"] = str(body.get("speak") or f"Attenzione! {data['title'] or 'Allarme'} {where}.")[:200]
    desk.show("alarm", data, key=key, priority=int(body.get("priority", 100)))
    if red:
        redalert.trigger(data["speak"] + (" " + data["message"] if data["message"] else ""))
    store.event("ERROR", f"ALLARME {kind} {data['room']}: {data['message']}", "alarm")
    return {"ok": True, "key": key}


@public_routes.get("/widgets/{wid}/{name}")
async def widget_file(wid: str, name: str):
    path = desk.file(wid, name)
    if not path:
        raise HTTPException(404, "Widget non trovato")
    return FileResponse(path, media_type=FILES[name], headers={"Cache-Control": "no-cache"})


@public_routes.post("/api/desk/idle")
async def desk_idle(request: Request):
    require_display(request, "Solo dal display o dal pannello")
    desk.went_idle()
    return {"ok": True}


@public_routes.post("/api/desk/wake")
async def desk_wake(request: Request):
    require_display(request, "Solo dal display")
    return {"ok": True, "closed": desk.wake()}


@public_routes.post("/api/desk/position")
async def desk_position(request: Request):
    require_display(request, "Solo dal display")
    body = await request.json()
    wid = str(body.get("id") or "")
    try:
        if body.get("clear"):
            desk.set_position(wid, None, None)
        else:
            x, y = float(body.get("x")), float(body.get("y"))
            desk.set_position(wid, x, y)
            from features.desktop.learner_bridge import bridge as learner
            learner.moved(wid, x, y)
    except (KeyError, TypeError, ValueError):
        raise HTTPException(400, "Posizione non valida")
    return {"ok": True}


@public_routes.post("/api/desk/fullscreen")
async def desk_fullscreen(request: Request):
    require_display(request, "Solo dal display")
    body = await request.json()
    key = str(body.get("key") or "")[:120]
    on = bool(body.get("on", True))
    if desk.fullscreen(key, on) is None:
        raise HTTPException(404, "Widget non trovato")
    if on:
        from features.desktop.learner_bridge import bridge as learner
        learner.resized(key, "full")
    return {"ok": True}


@public_routes.post("/api/desk/close")
async def desk_close(request: Request):
    require_display(request, "Solo dal display")
    key = str((await request.json()).get("key") or "")[:120]
    from features.desktop.learner_bridge import bridge as learner
    learner.closed(key)
    if not desk.dismiss(key):
        raise HTTPException(404, "Widget non trovato")
    if key.startswith("alarm:"):
        from features.redalert.service import redalert
        redalert.stop()
    if key == "chess_3d" or key.startswith("chess"):
        try:
            from features.games.commands import close_chess
            close_chess()
        except Exception:
            pass
    return {"ok": True}


@public_routes.post("/api/desk/hello")
async def desk_hello(request: Request):
    require_display(request, "Solo dal display")
    body = await request.json()
    try:
        desk.screen_hello(max(0, min(16, int(body.get("screen", 0)))), int(body.get("x", 0)),
                          int(body.get("w", 0)), int(body.get("h", 0)),
                          bool(body.get("local")) and is_local(request), str(body.get("ear") or "")[:260],
                          str(body.get("perf") or "")[:420], request.client.host if request.client else "",
                          body.get("surface") if isinstance(body.get("surface"), dict) else None)
    except (TypeError, ValueError):
        raise HTTPException(400, "Schermo non valido")
    return {"ok": True}


@public_routes.post("/api/desk/screen")
async def desk_screen(request: Request):
    require_display(request, "Solo dal display")
    body = await request.json()
    wid, screen = str(body.get("id") or ""), body.get("screen")
    try:
        desk.set_screen(wid, None if screen is None else max(0, min(16, int(screen))))
    except KeyError:
        raise HTTPException(404, "Widget sconosciuto")
    except (TypeError, ValueError):
        raise HTTPException(400, "Schermo non valido")
    return {"ok": True}


@admin_routes.post("/api/alarm")
async def internal_alert(request: Request):
    require_internal(request)
    return _alert(await request.json())


@admin_routes.get("/api/widgets")
async def admin_widgets(_: str = Depends(require_admin)):
    desk.scan()
    return desk.listing()


@admin_routes.put("/api/widgets/{wid}")
async def admin_widget_set(wid: str, request: Request, _: str = Depends(require_admin)):
    try:
        desk.set_prefs(wid, await request.json())
    except KeyError:
        raise HTTPException(404, "Widget sconosciuto")
    except (TypeError, ValueError):
        raise HTTPException(400, "Valore non valido")
    return desk.listing()


@admin_routes.post("/api/widgets/{wid}/test")
async def admin_widget_test(wid: str, _: str = Depends(require_admin)):
    m = desk.widgets.get(wid)
    if not m:
        raise HTTPException(404, "Widget sconosciuto")
    if wid == "alarm":
        _alert({"kind": "generic", "test": True}, red=False)
        desk.instances[next(k for k in desk.instances if k.startswith("alarm:"))]["expires_at"] = time.time() + 20
    else:
        desk.show(wid, {}, key=f"test:{wid}", ttl=30)
    return desk.listing()


@admin_routes.get("/api/widgets/targets")
async def admin_widget_targets(_: str = Depends(require_admin)):
    from features.nodes.registry import registry
    targets = [{"id": "server", "name": "Server Principale", "type": "server"}]
    for n in registry.listing():
        if n.get("online") and n.get("type") in ("satellite", "display", "desktop"):
            targets.append({"id": n["id"], "name": n["name"], "type": n.get("type_label") or n.get("type")})
    return {"targets": targets}


@admin_routes.post("/api/widgets/{wid}/recall")
async def admin_widget_recall(wid: str, request: Request, _: str = Depends(require_admin)):
    if wid == "alarm":
        raise HTTPException(400, "L'allarme non si richiama a mano: usa la prova dal pannello")
    target = None
    if request.headers.get("content-type", "").startswith("application/json"):
        try:
            body = await request.json()
            target = body.get("target") if isinstance(body, dict) else None
        except Exception:
            pass
    try:
        origin = desk.recall(wid, target=target)
    except KeyError:
        raise HTTPException(404, "Widget sconosciuto")
    return {"ok": True, "origin": origin, "target": target}


@admin_routes.delete("/api/desk/{key:path}")
async def admin_desk_hide(key: str, _: str = Depends(require_admin)):
    desk.hide(key=key)
    return desk.listing()
