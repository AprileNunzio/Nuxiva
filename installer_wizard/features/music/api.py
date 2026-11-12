from fastapi import APIRouter, Depends, HTTPException, Request

from access import require_admin, require_internal
from config import write_env
from features.music import music
from orchestrator import orch
from state import store
from tasks import background

admin_routes = APIRouter()


def overview() -> dict:
    step = store.steps.get("music") or {}
    return {**music.watcher.summary(), "step": {"status": step.get("status"), "error": step.get("error", "")}}


@admin_routes.get("/api/music")
async def admin_music(_: str = Depends(require_admin)):
    return overview()


@admin_routes.put("/api/music")
async def admin_music_set(request: Request, user: str = Depends(require_admin)):
    enabled = bool((await request.json()).get("enabled"))
    write_env({"NUXIVA_MUSIC_ID": "1" if enabled else "0"})
    if not enabled:
        store.now_playing = {}
        store.touch()
    store.event("INFO", f"Riconoscimento musicale {'attivato' if enabled else 'disattivato'} da {user}", "music")
    background(orch.converge(["music"], reason="Riconoscimento musicale", force=enabled))
    return overview()


@admin_routes.get("/api/music/settings")
async def admin_music_get_settings(_: str = Depends(require_admin)):
    from feature_registry import registry
    registry.scan()
    return {"values": registry.settings_of("music")}


@admin_routes.put("/api/music/settings")
async def admin_music_save_settings(request: Request, user: str = Depends(require_admin)):
    from feature_registry import registry
    from settings import apply_config
    registry.scan()
    body = await request.json()
    try:
        env_updates, steps = registry.save_settings("music", body)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    applying = await apply_config(env_updates, user, steps) if env_updates else []
    return {"ok": True, "applying": applying, "values": registry.settings_of("music")}


@admin_routes.post("/api/internal/music")
async def internal_music(request: Request):
    require_internal(request)
    wav = await request.body()
    if not 1000 < len(wav) < 4_000_000:
        raise HTTPException(400, "Audio non valido")
    return await music.watcher.handle(wav)

