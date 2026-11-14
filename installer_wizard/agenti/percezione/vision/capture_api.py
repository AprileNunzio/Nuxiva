from capture_daemon import CaptureDaemon, embedder_from
from fastapi import APIRouter
from fastapi.responses import JSONResponse

PRESENCE_KEYS = ("available", "active", "scene", "app", "source")


def summary(daemon) -> dict:
    view = daemon.view() if daemon is not None else {"available": False}
    return {key: view.get(key) for key in PRESENCE_KEYS}


def webcam_source(vision):
    def frame():
        with vision.lock:
            return None if vision.raw is None else vision.raw.copy()

    return frame


def router(daemon) -> APIRouter:
    routes = APIRouter()

    @routes.get("/capture")
    async def view():
        return JSONResponse(daemon.view())

    @routes.post("/capture/wipe")
    async def wipe():
        daemon.wipe()
        return {"ok": True}

    return routes


def attach(app, vision, cfg) -> CaptureDaemon:
    daemon = CaptureDaemon(cfg, webcam_source(vision), embedder_from(cfg))
    vision.capture = daemon
    daemon.start()
    app.include_router(router(daemon))
    return daemon
