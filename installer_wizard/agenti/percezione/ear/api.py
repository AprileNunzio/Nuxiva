import base64
import binascii
import json
import os
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, WebSocket

from access import require_admin, require_display
from config import env_get
from agenti.desktop.desk import desk
from agenti.people import people
from agenti.ear import keycheck, proxy, wake_template
from agenti.ear.journal_api import routes as journal_routes
from agenti.ear.mictest_api import routes as mictest_routes
from state import store

public_routes = APIRouter()
admin_routes = APIRouter()
admin_routes.include_router(journal_routes)
admin_routes.include_router(mictest_routes)
REVIEW_DIR = Path(os.environ.get("NUXIVA_EAR_REVIEW_DIR", "/var/lib/nuxiva/ear_review"))
TUNING_FILE = Path(os.environ.get("NUXIVA_EAR_TUNING", "/var/lib/nuxiva/ear_tuning.json"))


def on(key: str, default: str) -> bool:
    return env_get(key, default).strip().lower() not in ("0", "off", "no", "false")


def captions_config() -> dict:
    def pick(key: str, default: str, allowed: tuple) -> str:
        value = env_get(key, default).strip().lower()
        return value if value in allowed else default

    try:
        hold = max(2.0, min(30.0, float(env_get("NUXIVA_CAPTIONS_HOLD", "6"))))
    except ValueError:
        hold = 6.0
    return {"enabled": on("NUXIVA_CAPTIONS", "1"), "scope": pick("NUXIVA_CAPTIONS_SCOPE", "all", ("all", "addressed")),
            "speaker": on("NUXIVA_CAPTIONS_SPEAKER", "1"), "size": pick("NUXIVA_CAPTIONS_SIZE", "medium", ("small", "medium", "large")),
            "hold": hold, "position": pick("NUXIVA_CAPTIONS_POSITION", "bottom", ("bottom", "center"))}


def speaker_names() -> dict:
    return {p["slug"]: people.display_name(p) for p in people.all_profiles(light=True)}


@public_routes.get("/api/ear/config")
@admin_routes.get("/api/ear/config")
async def ear_config(request: Request):
    require_display(request, "Solo dal display")
    agc = env_get("NUXIVA_MIC_AGC", "auto").strip().lower()
    return {"echoCancellation": on("NUXIVA_MIC_EC", "1"), "noiseSuppression": on("NUXIVA_MIC_NS", "0"),
            "autoGainControl": agc in ("1", "on", "yes", "true"), "autoLevel": agc == "auto",
            "captions": captions_config(), "speakers": speaker_names()}


@admin_routes.get("/api/ear/review")
async def ear_review(request: Request):
    require_admin(request)
    try:
        data = json.loads((REVIEW_DIR / "summary.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        data = {"state": "nessuna analisi ancora", "recording": on("NUXIVA_EAR_RECORD", "1"), "pending": 0, "summary": {"chunks": 0}}
    except (OSError, ValueError) as exc:
        data = {"state": f"riepilogo non leggibile: {exc}"}
    return data


@admin_routes.post("/api/ear/review/purge")
async def ear_purge(request: Request):
    require_admin(request)
    removed = 0
    for path in list((REVIEW_DIR / "chunks").glob("c*")) + list((REVIEW_DIR / "chunks").glob("*.tmp")):
        try:
            path.unlink()
            removed += 1
        except OSError as exc:
            store.event("WARN", f"Registrazione non eliminata ({path.name}): {exc}", "ear")
    store.event("INFO", f"Registrazioni dell'ascolto eliminate: {removed} file", "ear")
    return {"ok": True, "removed": removed}


@admin_routes.post("/api/ear/tuning/reset")
async def ear_tuning_reset(request: Request):
    require_admin(request)
    TUNING_FILE.unlink(missing_ok=True)
    store.event("INFO", "Regolazioni automatiche dell'ascolto azzerate", "ear")
    return {"ok": True}

@admin_routes.post("/api/ear/stt/check")
async def ear_stt_check(request: Request):
    require_admin(request)
    body = await request.json()
    try:
        return await keycheck.check(str(body.get("provider") or ""), str(body.get("key") or "")[:300],
                                    str(body.get("url") or "")[:300])
    except keycheck.KeyCheckError as exc:
        raise HTTPException(400, str(exc))


desk.register_source("ear_widget", lambda: {"ear": True} if env_get("NUXIVA_EAR", "1") != "0" else None)


WAKE_MODELS = Path(os.environ.get("NUXIVA_WAKEWORD_MODELS", "/opt/nuxiva-ear/wakeword"))


@admin_routes.post("/api/ear/wake-template")
async def ear_wake_template(request: Request):
    require_admin(request)
    if int(request.headers.get("content-length") or 0) > 2 * 1024 * 1024:
        raise HTTPException(413, "payload_too_large")
    body = await request.json()
    raw = body.get("takes") if isinstance(body, dict) else None
    if not isinstance(raw, list) or not 3 <= len(raw) <= wake_template.MAX_TAKES:
        raise HTTPException(400, "wake.error.recordings")
    try:
        takes = [base64.b64decode(str(item), validate=True) for item in raw]
    except (binascii.Error, ValueError):
        raise HTTPException(400, "wake.error.recordings")
    if not wake_template.available():
        raise HTTPException(503, "wake.error.engine_unavailable")
    from identity import assistant_name
    try:
        data = wake_template.enroll(takes)
        wake_template.save(wake_template.model_path(WAKE_MODELS, wake_template.candidates(assistant_name(), os.environ.get("NUXIVA_WAKEWORD_MODEL", ""))[0]), data)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    store.event("INFO", "Parola di attivazione addestrata sulla voce dell'utente", "ear")
    return {"ok": True, "takes": len(takes)}


@public_routes.post("/api/ear/client")
async def ear_client(request: Request):
    require_display(request, "Solo dal display")
    body = await request.json()
    error = str(body.get("error") or "")[:160]
    previous = getattr(store, "mic", None) or {}
    store.mic = {"ok": bool(body.get("ok")), "error": error, "inputs": int(body.get("inputs") or 0),
                 "label": str(body.get("label") or "")[:80], "at": time.time()}
    if error and error != previous.get("error"):
        store.event("WARN", f"Microfono del display: {error}", "ear")
    elif body.get("ok") and previous.get("error"):
        store.event("INFO", f"Microfono del display di nuovo attivo: {store.mic['label'] or 'predefinito'}", "ear")
    return {"ok": True}


@public_routes.websocket("/ws/ear")
@admin_routes.websocket("/ws/ear")
async def ear_socket(socket: WebSocket):
    await proxy.proxy(socket)
