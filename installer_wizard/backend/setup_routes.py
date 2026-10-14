import json
import time
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from access import NO_CACHE
from config import DEMO, read_env
from setup_session import session_manager
from setup_telemetry import telemetry_routes
import setup_owner

router = APIRouter()
router.include_router(telemetry_routes)

@router.get("/api/setup/session")
async def get_setup_session():
    return JSONResponse(session_manager.to_dict(), headers=NO_CACHE)

@router.post("/api/setup/session/navigate")
async def navigate_setup_session(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON payload")
    target = int(body.get("target_step", 1))
    try:
        updated = session_manager.navigate(target)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return JSONResponse(updated, headers=NO_CACHE)

@router.post("/api/setup/session/update")
async def update_setup_session(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON payload")
    step = int(body.get("step", session_manager.current_step))
    updates = body.get("updates", {})
    if not isinstance(updates, dict):
        raise HTTPException(400, "Updates must be a dictionary")
    try:
        updated = session_manager.update_config(step, updates)
    except Exception as e:
        raise HTTPException(400, str(e))
    return JSONResponse(updated, headers=NO_CACHE)

@router.post("/api/setup/finalize")
async def finalize_setup(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    from settings import apply_config
    cfg = session_manager.config
    assistant_name = str(body.get("assistant_name") or cfg.get("assistant_name") or "Aria").strip()
    clean_name = assistant_name.lower().replace("hey ", "").replace("ehi ", "").strip()
    primary = clean_name or "nuxiva"
    aliases = cfg.get("wake_phonetic_aliases") or [primary]
    if primary not in aliases:
        aliases.insert(0, primary)
    env_updates = {
        "NUXIVA_ASSISTANT_NAME": assistant_name,
        "NUXIVA_ASSISTANT_GENDER": str(cfg.get("assistant_gender", "female")),
        "NUXIVA_VOICE": str(cfg.get("voice_id", "if_sara")),
        "NUXIVA_UI_LANG": str(cfg.get("locale", "it-IT")).split("-")[0].lower(),
        "NUXIVA_MIC_NOISE_FLOOR_DB": str(cfg.get("mic_noise_floor_db", -58.2)),
        "NUXIVA_MIC_SNR_DB": str(cfg.get("mic_snr_db", 27.4)),
        "NUXIVA_MIC_GAIN_DB": str(cfg.get("mic_gain_db", 4.5)),
        "NUXIVA_MIC_VAD_THRESHOLD": str(cfg.get("mic_vad_threshold", 0.28)),
        "NUXIVA_WAKE_PHONETIC_ALIASES": ",".join(aliases),
        "NUXIVA_BRAIN_PRESET": str(cfg.get("brain_preset", "nuxiva-6.5-auto"))
    }
    owner_name = str(cfg.get("owner_name") or body.get("owner_name") or "").strip()
    owner_last = str(cfg.get("owner_last") or body.get("owner_last") or "").strip()
    if owner_name:
        env_updates["NUXIVA_USER_NAME"] = owner_name
        setup_owner.register_owner(owner_name, owner_last, env_updates["NUXIVA_UI_LANG"], env_updates["NUXIVA_UI_LANG"])
    await apply_config(env_updates, "master blueprint setup wizard")
    from state import store
    import setup_api
    setup_api._mark_done("master blueprint setup wizard")
    try:
        from nuxiva_bus import bus
        bus.publish("setup.completed", {"at": time.time(), "assistant_name": assistant_name})
        bus.publish("identity.assistant_renamed", {"assistant_name": assistant_name, "wake_word_primary": primary})
    except Exception:
        pass
    return JSONResponse({
        "ok": True,
        "assistant_name": assistant_name,
        "wake_word_primary": primary,
        "status": "online"
    }, headers=NO_CACHE)
