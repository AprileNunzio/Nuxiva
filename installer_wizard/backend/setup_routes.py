import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

import setup_audio
import setup_probe
import setup_purposes
from access import NO_CACHE
from config import STATE_DIR
from sealed import write_private
from setup_session import STEPS, session_manager

log = logging.getLogger("nuxiva.setup")
router = APIRouter()
SAMPLES_DIR = STATE_DIR / "wakeword_samples"
FACE_KINDS = ("front", "three_left", "three_right")
WAKE_SHOTS = 3


def require_open(request: Request) -> None:
    import setup_api
    setup_api.require_setup(request)


async def _json(request: Request) -> dict:
    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(400, "Dati JSON non validi")
    if not isinstance(body, dict):
        raise HTTPException(400, "Dati JSON non validi")
    return body


def _step(value: object) -> int:
    try:
        step = int(value)
    except (TypeError, ValueError):
        raise HTTPException(400, "Passo non valido")
    if not 1 <= step <= STEPS:
        raise HTTPException(400, "Passo non valido")
    return step


@router.get("/api/setup/session")
async def get_setup_session(_: None = Depends(require_open)):
    return JSONResponse(session_manager.to_dict(), headers=NO_CACHE)


@router.post("/api/setup/session/navigate")
async def navigate_setup_session(request: Request, _: None = Depends(require_open)):
    body = await _json(request)
    try:
        return JSONResponse(session_manager.navigate(_step(body.get("target_step"))), headers=NO_CACHE)
    except ValueError as exc:
        raise HTTPException(409, str(exc))


@router.post("/api/setup/session/update")
async def update_setup_session(request: Request, _: None = Depends(require_open)):
    body = await _json(request)
    updates = body.get("updates", {})
    if not isinstance(updates, dict):
        raise HTTPException(400, "Gli aggiornamenti devono essere un dizionario")
    try:
        return JSONResponse(session_manager.update(_step(body.get("step")), updates), headers=NO_CACHE)
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, str(exc))


@router.get("/api/setup/hardware")
async def setup_hardware(_: None = Depends(require_open)):
    return JSONResponse(setup_probe.hardware_report(), headers=NO_CACHE)


@router.post("/api/setup/cameras/scan")
async def setup_cameras(_: None = Depends(require_open)):
    result = await setup_probe.scan_cameras()
    session_manager.record("cameras", result["devices"])
    return JSONResponse(result, headers=NO_CACHE)


@router.post("/api/setup/face")
async def setup_face(request: Request, _: None = Depends(require_open)):
    from features.people import people, views
    import setup_owner
    kind = str(request.query_params.get("kind") or "")
    if kind not in FACE_KINDS:
        raise HTTPException(400, "Vista del volto non valida")
    cfg = session_manager.config
    first, last = setup_owner.clean_names({"name": cfg.get("owner_name"), "last_name": cfg.get("owner_last"),
                                           "assistant_name": cfg.get("assistant_name")})
    name = setup_owner.full_name(first, last)
    slug = people.slugify(name)
    people.ensure(slug, name)
    resp = await views._forward(f"/people/{slug}/views/capture", {"kind": kind, "name": name}, None, 30)
    if resp.status_code in (404, 502, 503):
        raise HTTPException(503, "Servizio di visione o telecamera del server non disponibile: potrai registrare il volto più tardi da Persone e Presenze")
    if resp.status_code != 200:
        return resp
    done = sorted(set(cfg.get("face_views") or []) | {kind})
    session_manager.record("face_views", done)
    try:
        detail = json.loads(resp.body or b"{}")
    except ValueError:
        detail = {}
    return JSONResponse({"ok": True, "kind": kind, "views": done, "vision": detail}, headers=NO_CACHE)


async def _read_audio(request: Request) -> bytes:
    if request.headers.get("content-type", "").split(";")[0].strip() not in ("audio/wav", "audio/x-wav"):
        raise HTTPException(415, "Invia la registrazione come WAV")
    data = bytearray()
    async for chunk in request.stream():
        data += chunk
        if len(data) > setup_audio.MAX_BYTES:
            raise HTTPException(413, "Registrazione troppo lunga")
    return bytes(data)


@router.post("/api/setup/wake-sample")
async def setup_wake_sample(request: Request, _: None = Depends(require_open)):
    import setup_complete
    index = _step(request.query_params.get("index"))
    if index > WAKE_SHOTS:
        raise HTTPException(400, "Registrazione non valida")
    word = setup_complete.wake_word(session_manager.config.get("assistant_name") or "")
    if not word:
        raise HTTPException(409, "Scegli prima il nome dell'assistente")
    data = await _read_audio(request)
    try:
        metrics = setup_audio.analyze(data)
    except setup_audio.AudioRejected as exc:
        raise HTTPException(422, str(exc))
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    write_private(SAMPLES_DIR / f"{index}.wav", data)
    learned = False
    if metrics["usable"]:
        from features.ear import learner as learner_mod
        learned = learner_mod.learner.teach(word)
    samples = dict(session_manager.config.get("wake_samples") or {})
    samples[str(index)] = {**metrics, "word": word, "learned": learned}
    session_manager.record("wake_samples", samples)
    return JSONResponse({"index": index, **samples[str(index)]}, headers=NO_CACHE)


@router.post("/api/setup/plan")
async def setup_plan(request: Request, _: None = Depends(require_open)):
    body = await _json(request)
    try:
        plan = setup_purposes.build(body.get("purposes") or [], body.get("consents") or {}, body.get("skip") or [])
    except setup_purposes.PlanError as exc:
        raise HTTPException(400, str(exc))
    return JSONResponse(plan.to_dict(), headers=NO_CACHE)


@router.post("/api/setup/finalize")
async def finalize_setup(request: Request, _: None = Depends(require_open)):
    import setup_complete
    cfg, secrets = session_manager.config, session_manager.secrets
    lang = str(cfg.get("locale") or "it-IT")[:2]
    from setup_config import VOICES_BY_LANG_GENDER
    raw = {"name": cfg.get("owner_name"), "last_name": cfg.get("owner_last"), "assistant_name": cfg.get("assistant_name"),
           "assistant_gender": cfg.get("assistant_gender"), "lang": lang,
           "voice": VOICES_BY_LANG_GENDER.get(lang, {}).get(cfg.get("assistant_gender") or "female", "if_sara"),
           "brain": cfg.get("brain"), "profile": cfg.get("profile"), "ollama_url": cfg.get("ollama_url"),
           "cloud_provider": cfg.get("cloud_provider"), "cloud_key": secrets.get("cloud_key", ""),
           "packages": cfg.get("packages") or [], "purposes": cfg.get("purposes") or [], "consents": cfg.get("consents") or {},
           "skip": cfg.get("skip") or [], "ha_url": cfg.get("ha_url"), "ha_token": secrets.get("ha_token", "")}
    result = await setup_complete.complete(raw, request, "procedura guidata")
    session_manager.clear()
    return JSONResponse(result, headers=NO_CACHE)
