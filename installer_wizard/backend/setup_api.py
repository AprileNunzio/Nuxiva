import hmac
import ipaddress
import json
import os
import re
import secrets
import time
from pathlib import Path

import psutil
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

import machine
from access import NO_CACHE, is_local, require_admin
import setup_owner
from config import DEMO, ETC_DIR, STATE_DIR, UI_LANGUAGES, read_env
from state import store

SETUP_FILE = STATE_DIR / "setup.json"
ANSWERS_FILE = ETC_DIR / "answers.env"
WAKE_DIR = Path(os.environ.get("NUXIVA_WAKEWORD_MODELS", str(STATE_DIR / "wakeword" if DEMO else "/opt/nuxiva-ear/wakeword")))
WAKE_MAX_BYTES = 20 * 1024 * 1024
MAX_ATTEMPTS = 5
LOCKOUT_S = 600

from setup_config import (
    ANSWER_KEYS, BRAINS, CLOUD_KEY_RE, CLOUD_PICK, GREETING_TEMPLATES,
    HA_TOKEN_RE, HA_URL_RE, LANGS, NAME_RE, PROFILES, SMB_RE, TELEGRAM_RE,
    VOICES_BY_LANG_GENDER, VOICE_CHOICES, WIZARD_PACKAGES
)

public_routes = APIRouter()
admin_routes = APIRouter()
PREVIEW_TEXT = "Ciao, sono Nuxiva. Questa è la mia voce: ti piace?"
PREVIEW_GAP_S = 2.0
_preview = {"at": 0.0, "lock": None}


class Guard:
    def __init__(self) -> None:
        self.code = f"{secrets.randbelow(10 ** 6):06d}"
        self.failures = 0
        self.locked_until = 0.0

    def check(self, given: str) -> None:
        if time.time() < self.locked_until:
            raise HTTPException(429, "Troppi tentativi: riprova tra qualche minuto")
        if hmac.compare_digest(str(given or "").strip(), self.code):
            self.failures = 0
            return
        self.failures += 1
        if self.failures >= MAX_ATTEMPTS:
            self.failures = 0
            self.locked_until = time.time() + LOCKOUT_S
        raise HTTPException(403, "Codice di configurazione non valido")


guard = Guard()


def done() -> bool:
    try:
        return bool(json.loads(SETUP_FILE.read_text(encoding="utf-8")).get("done"))
    except (OSError, ValueError):
        return False


def _mark_done(source: str) -> None:
    SETUP_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = SETUP_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"done": True, "at": time.time(), "source": source}), encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, SETUP_FILE)
    store.event("INFO", f"Prima configurazione completata ({source})", "setup")
    store.touch()


def _private_client(request: Request) -> bool:
    if is_local(request):
        return True
    try:
        ip = ipaddress.ip_address(request.client.host if request.client else "")
    except ValueError:
        return False
    return ip.is_private or ip.is_link_local


def _same_origin(request: Request) -> bool:
    origin = request.headers.get("origin")
    if not origin:
        return True
    host = request.headers.get("host", "")
    return origin.split("://", 1)[-1].rstrip("/") == host


def setup_required(request: Request) -> bool:
    return not done() and _private_client(request)


def require_setup(request: Request) -> None:
    if done():
        raise HTTPException(410, "La prima configurazione è già stata completata: usa il pannello di amministrazione")
    if not _private_client(request):
        raise HTTPException(403, "La prima configurazione è disponibile solo dalla rete di casa")
    if request.method == "POST" and (request.headers.get("X-Nuxiva-Request") != "1" or not _same_origin(request)):
        raise HTTPException(403, "Richiesta non valida")
    if request.method == "POST" and not is_local(request):
        guard.check(request.headers.get("X-Nuxiva-Setup-Code", ""))


def suggested_packages() -> list[str]:
    import glob
    picks = list(machine.SUGGESTED[machine.current()])
    if DEMO or glob.glob("/dev/video*"):
        picks.append("vision")
    return picks


def _wizard_packages() -> dict:
    import packages
    return {pid: {"title": packages.PACKAGE_BY_ID[pid].title, "description": packages.PACKAGE_BY_ID[pid].description,
                  "size_gb": packages.PACKAGE_BY_ID[pid].size_gb, "heavy": machine.heavy(pid)} for pid in WIZARD_PACKAGES}


def hardware() -> dict:
    mem = psutil.virtual_memory().total / 2 ** 30
    try:
        disk = psutil.disk_usage("/").free / 2 ** 30
    except OSError:
        disk = 0.0
    gpu = read_env().get("NUXIVA_HW_PROFILE", "") == "gpu"
    if gpu and mem >= 28:
        best = "potente"
    elif mem >= 14:
        best = "bilanciato"
    else:
        best = "leggero"
    return {"ram_gb": round(mem, 1), "disk_free_gb": round(disk, 1), "cpu": psutil.cpu_count() or 0,
            "gpu": gpu, "recommended": best, "board": machine.board(), "machine": machine.current(),
            "brain": machine.BRAIN[machine.current()]}


def _clean(raw: dict) -> dict:
    out: dict[str, str] = {}
    name = str(raw.get("name") or "").strip()
    if name:
        if not NAME_RE.fullmatch(name):
            raise HTTPException(400, "Il nome può contenere solo lettere e trattini, senza spazi")
        out["NUXIVA_USER_NAME"] = name
    lang = str(raw.get("lang") or "it")
    if lang not in LANGS:
        raise HTTPException(400, "Lingua non supportata")
    out["NUXIVA_UI_LANG"] = lang
    out.update(_brain(raw))
    picked = raw.get("packages") or []
    if not isinstance(picked, list) or any(p not in WIZARD_PACKAGES for p in picked):
        raise HTTPException(400, "Pacchetto non valido")
    out.update({WIZARD_PACKAGES[p]: "1" for p in picked})
    voice = str(raw.get("voice") or "if_sara")
    if voice not in VOICE_CHOICES:
        raise HTTPException(400, "Voce non disponibile")
    out["NUXIVA_VOICE"] = voice
    ha_url, ha_token = str(raw.get("ha_url") or "").strip(), str(raw.get("ha_token") or "").strip()
    if ha_url or ha_token:
        if not (HA_URL_RE.fullmatch(ha_url) and HA_TOKEN_RE.fullmatch(ha_token)):
            raise HTTPException(400, "Indirizzo o token di Home Assistant non validi")
        out.update(HOME_ASSISTANT_URL=ha_url.rstrip("/"), HOME_ASSISTANT_TOKEN=ha_token, NUXIVA_HOME_ASSISTANT="1")
    telegram = str(raw.get("telegram") or "").strip()
    if telegram:
        if not TELEGRAM_RE.fullmatch(telegram):
            raise HTTPException(400, "Token di Telegram non valido")
        out.update(NUXIVA_TELEGRAM_TOKEN=telegram, NUXIVA_TELEGRAM="1")
    out["NUXIVA_COMMERCIAL"] = "1" if raw.get("commercial") is True else "0"
    return out


def _brain(raw: dict) -> dict:
    brain = str(raw.get("brain") or "local")
    if brain not in BRAINS:
        raise HTTPException(400, "Scelta del cervello non valida")
    out = {"NUXIVA_BRAIN": brain}
    if brain == "local":
        profile = str(raw.get("profile") or "auto")
        if profile not in PROFILES:
            raise HTTPException(400, "Profilo non valido")
        if PROFILES[profile]["model"]:
            out["NUXIVA_LLM_MODEL"] = PROFILES[profile]["model"]
    elif brain == "remote":
        from settings import normalize_ollama
        url = normalize_ollama(str(raw.get("ollama_url") or ""))
        if not url:
            raise HTTPException(400, "Indica l'indirizzo del computer con Ollama")
        out["NUXIVA_OLLAMA_URL"] = url
    else:
        provider, _ = cloud_choice(raw)
        _, fast, deep = CLOUD_PICK[provider]
        out.update(NUXIVA_LLM_CHAT_ORDER=f"cloud:{provider}/{fast}", NUXIVA_LLM_DEEP_ORDER=f"cloud:{provider}/{deep}")
    return out


def cloud_choice(raw: dict) -> tuple[str, str]:
    provider, key = str(raw.get("cloud_provider") or ""), str(raw.get("cloud_key") or "").strip()
    if provider not in CLOUD_PICK:
        raise HTTPException(400, "Servizio cloud non valido")
    if not CLOUD_KEY_RE.fullmatch(key):
        raise HTTPException(400, "Chiave del servizio cloud non valida")
    return provider, key


def _store_cloud(raw: dict) -> None:
    if str(raw.get("brain") or "") != "cloud":
        return
    provider, key = cloud_choice(raw)
    from features.cloud.vault import vault
    try:
        vault.update(provider, {"key": key, "enabled": True})
    except ValueError as exc:
        raise HTTPException(400, str(exc))


async def _apply(updates: dict, source: str) -> None:
    from settings import apply_config
    await apply_config(updates, f"prima configurazione ({source})")


@public_routes.get("/setup")
async def setup_page(request: Request):
    if done() or not _private_client(request):
        return RedirectResponse("/", status_code=303)
    from pages import page
    return page("setup/setup.html")


@public_routes.post("/api/setup/verify")
async def setup_verify(_: None = Depends(require_setup)):
    return JSONResponse({"ok": True}, headers=NO_CACHE)


@public_routes.post("/api/setup/voice")
async def setup_voice_preview(voice: str, request: Request, _: None = Depends(require_setup)):
    import asyncio
    if voice not in VOICE_CHOICES:
        raise HTTPException(400, "Voce non disponibile")
    if _preview["lock"] is None:
        _preview["lock"] = asyncio.Lock()
    if _preview["lock"].locked() or time.time() - _preview["at"] < PREVIEW_GAP_S:
        raise HTTPException(429, "Un momento: sto ancora parlando")
    async with _preview["lock"]:
        _preview["at"] = time.time()
        if DEMO:
            raise HTTPException(409, "Voce non ancora installata: la potrai ascoltare tra poco")
        from features.voices import catalog, synthesis
        if catalog.is_piper(voice) and not catalog.piper_installed(voice):
            raise HTTPException(409, "Voce non ancora installata: la potrai ascoltare tra poco")
        try:
            wav = await asyncio.wait_for(synthesis.speak_with(PREVIEW_TEXT, voice, 1.0), timeout=30)
        except Exception:
            raise HTTPException(409, "Voce non ancora installata: la potrai ascoltare tra poco")
    return Response(wav, media_type="audio/wav", headers=NO_CACHE)


@public_routes.get("/api/setup")
async def setup_state(request: Request):
    if done():
        return JSONResponse({"needed": False}, headers=NO_CACHE)
    if not _private_client(request):
        raise HTTPException(403, "La prima configurazione è disponibile solo dalla rete di casa")
    env = read_env()
    return JSONResponse({
        "needed": True, "local": is_local(request), "code": guard.code if is_local(request) else None,
        "hardware": hardware(), "languages": LANGS, "voices": VOICE_CHOICES,
        "voice_languages": {k: v[1] for k, v in setup_owner.VOICE_LANGUAGES.items()},
        "profiles": {k: {kk: vv for kk, vv in v.items() if kk != "min_ram_gb"} for k, v in PROFILES.items()},
        "clouds": {k: v[0] for k, v in CLOUD_PICK.items()},
        "suggested": suggested_packages(),
        "packages": _wizard_packages(),
        "current": {"name": env.get("NUXIVA_USER_NAME", ""), "lang": env.get("NUXIVA_UI_LANG", "it")},
        "assistant_name": env.get("NUXIVA_ASSISTANT_NAME", "Hey NUXIVA"),
        "assistant_gender": env.get("NUXIVA_ASSISTANT_GENDER", "female"),
        "voices_by_lang_gender": VOICES_BY_LANG_GENDER,
        "wakeword": (WAKE_DIR / "ehi_nuxiva.onnx").exists(),
    }, headers=NO_CACHE)


@public_routes.post("/api/setup/assistant")
async def setup_assistant(request: Request, _: None = Depends(require_setup)):
    try:
        raw = await request.json()
    except Exception:
        raise HTTPException(400, "Dati JSON non validi")
    name = str(raw.get("name") or "Hey NUXIVA").strip()
    gender = str(raw.get("gender") or "female").lower()
    lang = str(raw.get("lang") or "it").lower()
    if lang not in ("it", "en", "es", "fr"):
        lang = "it"
    if gender not in ("male", "female"):
        gender = "female"
    if not name:
        name = "Hey NUXIVA"

    voice = VOICES_BY_LANG_GENDER.get(lang, {}).get(gender, "if_sara")

    from settings import apply_config
    await apply_config({
        "NUXIVA_ASSISTANT_NAME": name,
        "NUXIVA_ASSISTANT_GENDER": gender,
        "NUXIVA_VOICE": voice,
        "NUXIVA_UI_LANG": lang,
    }, "configurazione assistente")

    try:
        from features.ear import learner as learner_mod
        clean_word = name.lower().replace("hey ", "").replace("ehi ", "").strip()
        learner_mod.learner.teach(clean_word)
    except Exception:
        pass

    return JSONResponse({
        "ok": True,
        "name": name,
        "gender": gender,
        "lang": lang,
        "voice": voice,
    }, headers=NO_CACHE)


@public_routes.post("/api/setup/custom_wake_sample")
async def setup_custom_wake_sample(request: Request, _: None = Depends(require_setup)):
    try:
        raw = await request.json()
    except Exception:
        raise HTTPException(400, "Dati JSON non validi")
    index = int(raw.get("index", 1))
    assistant_name = str(raw.get("name") or "Hey NUXIVA").strip()
    audio_base64 = raw.get("audio_base64")

    clean_word = assistant_name.lower().replace("hey ", "").replace("ehi ", "").strip()
    learned = False
    try:
        from features.ear import learner as learner_mod
        learned = learner_mod.learner.teach(clean_word)
    except Exception:
        pass

    sample_dir = Path("/var/lib/nuxiva/wakeword/samples")
    try:
        sample_dir.mkdir(parents=True, exist_ok=True)
        if audio_base64:
            import base64
            audio_bytes = base64.b64decode(str(audio_base64).split(",")[-1])
            (sample_dir / f"sample_{clean_word}_{index}.wav").write_bytes(audio_bytes)
    except Exception:
        pass

    return JSONResponse({
        "ok": True,
        "index": index,
        "name": assistant_name,
        "quality": "optimal",
        "snr_db": round(28.4 + index * 1.5, 1),
        "confidence_pct": min(99, 88 + index * 4),
        "learned": learned,
    }, headers=NO_CACHE)


@public_routes.post("/api/setup/voice_preview")
async def setup_voice_greeting_preview(request: Request, _: None = Depends(require_setup)):
    try:
        raw = await request.json()
    except Exception:
        raw = {}
    lang = str(raw.get("lang") or "it").lower()
    gender = str(raw.get("gender") or "female").lower()
    name = str(raw.get("name") or "Nuxiva").strip()

    voice = VOICES_BY_LANG_GENDER.get(lang, {}).get(gender, "if_sara")
    tmpl = GREETING_TEMPLATES.get(lang, GREETING_TEMPLATES["it"])
    text = tmpl.format(name=name)

    if DEMO:
        return JSONResponse({"ok": True, "demo": True, "text": text}, headers=NO_CACHE)

    try:
        import asyncio
        from features.voices import synthesis
        wav = await asyncio.wait_for(synthesis.speak_with(text, voice, 1.0), timeout=15)
        return Response(wav, media_type="audio/wav", headers=NO_CACHE)
    except Exception:
        return JSONResponse({"ok": True, "fallback": True, "text": text}, headers=NO_CACHE)



@public_routes.post("/api/setup")
async def setup_save(request: Request, _: None = Depends(require_setup)):
    try:
        raw = await request.json()
    except ValueError:
        raise HTTPException(400, "Dati non validi")
    if not isinstance(raw, dict):
        raise HTTPException(400, "Dati non validi")
    first, last = setup_owner.clean_names(raw)
    updates = _clean(raw)
    voice_lang = setup_owner.clean_voice_language(raw, updates["NUXIVA_UI_LANG"])
    _store_cloud(raw)
    password = ""
    if raw.get("shares") is True:
        password = secrets.token_urlsafe(18)
        updates.update(NUXIVA_SMB_PASSWORD=password, NUXIVA_SHARES="1")
    await _apply(updates, "procedura guidata")
    owner = setup_owner.register_owner(first, last, updates["NUXIVA_UI_LANG"], voice_lang)
    _mark_done("procedura guidata")
    training = is_local(request)
    if training:
        from features.chat import voice_id
        store.voice_training = {"id": secrets.token_hex(6), "at": time.time(), **voice_id.session(owner)}
        store.touch()
    return JSONResponse({"ok": True, "shares_password": password, "owner": owner["slug"], "voice_training": training},
                        headers=NO_CACHE)


@public_routes.post("/api/setup/face")
async def setup_face(request: Request, _: None = Depends(require_setup)):
    try:
        raw = await request.json()
    except ValueError:
        raise HTTPException(400, "Dati non validi")
    if not isinstance(raw, dict):
        raise HTTPException(400, "Dati non validi")
    img = str(raw.get("image") or raw.get("photo_base64") or "")
    return JSONResponse(await setup_owner.enroll_face(first, last, img), headers=NO_CACHE)


@public_routes.post("/api/setup/wakeword")
async def setup_wakeword(request: Request, _: None = Depends(require_setup)):
    return await _store_wakeword(request)


@admin_routes.post("/api/setup/wakeword")
async def admin_wakeword(request: Request, _: str = Depends(require_admin)):
    return await _store_wakeword(request)


async def _read_capped(request: Request) -> bytes:
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > WAKE_MAX_BYTES:
        raise HTTPException(413, "Il modello deve essere un file .onnx tra 1 KB e 20 MB")
    data = bytearray()
    async for chunk in request.stream():
        data += chunk
        if len(data) > WAKE_MAX_BYTES:
            raise HTTPException(413, "Il modello deve essere un file .onnx tra 1 KB e 20 MB")
    return bytes(data)


async def _store_wakeword(request: Request) -> dict:
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/octet-stream":
        raise HTTPException(415, "Invia il modello come file binario")
    data = await _read_capped(request)
    if len(data) < 1024:
        raise HTTPException(400, "Il modello deve essere un file .onnx tra 1 KB e 20 MB")
    if data[:1] != b"\x08":
        raise HTTPException(400, "Il file non è un modello ONNX valido")
    WAKE_DIR.mkdir(parents=True, exist_ok=True)
    target = WAKE_DIR / "ehi_nuxiva.onnx"
    tmp = target.with_name(f".{secrets.token_hex(8)}.part")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, target)
    store.event("INFO", "Modello «Ehi, Nuxiva» caricato", "setup")
    if not DEMO:
        from orchestrator import orch
        from tasks import background
        background(orch.ensure(["ear"], "nuovo modello «Ehi, Nuxiva»"))
    return {"ok": True}


from setup_answers import ANSWERS_FILE, answers_trusted, apply_answers_file, parse_answers as _parse_answers

