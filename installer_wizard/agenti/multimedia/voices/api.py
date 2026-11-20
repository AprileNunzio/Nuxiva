import asyncio
import logging
import re

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from access import NO_CACHE, lang_of, require_admin, require_display
from config import env_get, write_env
from agenti.people import people
from agenti.study import study
from agenti.voices import catalog, downloads, languages, overview, playback, synthesis
from agenti.voices.audio_vault import COMMON_PHRASES, audio_vault
from agenti.voices import elevenlabs_client
from state import store

public_routes = APIRouter()
admin_routes = APIRouter()
logger = logging.getLogger("nuxiva.voices.api")
_VOICE_RE = re.compile(r"^[A-Za-z0-9_-]{2,60}$")


async def tts_response(text: str, lang: str | None = None) -> Response:
    study.engine.activity("voce")
    chosen_voice, chosen_speed, chosen_pitch, chosen_volume = None, None, None, None
    for p in store.presence.get("people", []):
        profile = people.load(p["slug"]) if p.get("known") else None
        if profile and profile.get("voice"):
            chosen_voice = profile["voice"].get("tts_voice") or None
            chosen_speed = float(profile["voice"].get("speed") or 0) or None
            chosen_pitch = profile["voice"].get("pitch")
            chosen_volume = profile["voice"].get("volume")
            break
    try:
        wav = await synthesis.synthesize(text, chosen_voice, chosen_speed, lang,
                                         pitch=float(chosen_pitch) if chosen_pitch not in (None, "") else None,
                                         volume=float(chosen_volume) if chosen_volume not in (None, "") else None)
    except ValueError:
        raise HTTPException(400, "Testo vuoto")
    except (RuntimeError, asyncio.TimeoutError) as exc:
        raise HTTPException(503, f"Voce neurale non disponibile: {exc}")
    return Response(wav, media_type="audio/wav", headers=NO_CACHE)


@public_routes.post("/api/assistant/tts")
async def public_tts(request: Request):
    require_display(request)
    body = await request.json()
    return await tts_response(str(body.get("text", "")), lang_of(body))


@admin_routes.post("/api/assistant/tts")
async def admin_tts(request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    return await tts_response(str(body.get("text", "")), lang_of(body))


@public_routes.post("/api/voice/speak")
async def public_voice_speak(request: Request):
    body = await request.json()
    text = str(body.get("text", "")).strip()
    if not text:
        raise HTTPException(400, "Testo vuoto")
    lang = lang_of(body)
    try:
        wav = await synthesis.synthesize(text, lang=lang)
    except (ValueError, RuntimeError, OSError) as exc:
        raise HTTPException(503, f"Voce neurale non disponibile: {exc}")
    ok = await playback.play_host_audio(wav)
    return {"ok": ok, "text": text, "lang": lang}


@admin_routes.post("/api/voice/speak")
async def admin_voice_speak(request: Request, _: str = Depends(require_admin)):
    return await public_voice_speak(request)


@admin_routes.get("/api/voices")
async def admin_voices(_: str = Depends(require_admin)):
    return await overview.overview()


@admin_routes.put("/api/voices")
async def admin_voices_set(request: Request, user: str = Depends(require_admin)):
    order = [str(v).strip() for v in (await request.json()).get("order", []) if str(v).strip()]
    if len(order) > 12 or not all(_VOICE_RE.match(v) for v in order):
        raise HTTPException(400, "Elenco di voci non valido")
    order = list(dict.fromkeys(order))
    write_env({"NUXIVA_VOICE_ORDER": ",".join(order), **({"NUXIVA_VOICE": order[0]} if order else {})})
    store.event("INFO", f"Ordine delle voci aggiornato da {user}: {', '.join(order) or 'automatico'}", "voice")
    return await overview.overview()


@admin_routes.post("/api/voices/download")
async def admin_voice_download(request: Request, _: str = Depends(require_admin)):
    name = str((await request.json()).get("voice", "")).strip()
    if not catalog.is_piper(name) or name not in catalog.piper_catalog():
        raise HTTPException(400, "Voce non valida")
    await downloads.start_download(name)
    return {"ok": True}


@admin_routes.put("/api/voices/language")
async def admin_voice_language(request: Request, user: str = Depends(require_admin)):
    body = await request.json()
    lang, name = languages.base(str(body.get("lang", ""))), str(body.get("voice", "")).strip()
    if lang not in languages.LANGS or (name and not _VOICE_RE.match(name)):
        raise HTTPException(400, "Lingua o voce non valida")
    prefs = catalog.lang_prefs()
    prefs.pop(lang, None)
    if name:
        prefs[lang] = name
        await downloads.start_download(name)
    write_env({"NUXIVA_VOICE_LANG": catalog.lang_prefs_env(prefs)})
    store.event("INFO", f"Voce per {languages.label(lang).lower()} impostata da {user}: {name or 'automatica'}", "voice")
    return await overview.overview()


@admin_routes.post("/api/voices/ensure")
async def admin_voice_ensure(request: Request, _: str = Depends(require_admin)):
    lang = languages.base(str((await request.json()).get("lang", "")))
    if lang not in languages.LANGS:
        raise HTTPException(400, "Lingua non valida")
    return await downloads.ensure_language(lang)


@admin_routes.delete("/api/voices/{name}")
async def admin_voice_delete(name: str, _: str = Depends(require_admin)):
    if not catalog.is_piper(name):
        raise HTTPException(400, "Solo le voci Piper scaricate possono essere eliminate")
    if name in catalog.custom_order():
        raise HTTPException(409, "La voce è nell'elenco di priorità: toglila prima dall'elenco")
    try:
        downloads.delete_piper(name)
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    return await overview.overview()


@admin_routes.post("/api/voices/preview")
async def admin_voice_preview(request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    name = str(body.get("voice", ""))
    if not _VOICE_RE.match(name):
        raise HTTPException(400, "Voce non valida")
    lang = catalog.describe(name)["lang"]
    text = synthesis.normalize(str(body.get("text") or catalog.SAMPLES.get(lang, catalog.SAMPLES["it"])), lang)[:300]
    if catalog.is_piper(name) and not catalog.piper_installed(name):
        raise HTTPException(409, "Voce non ancora scaricata")
    try:
        wav = await synthesis.speak_with(text, name, 1.0)
    except (httpx.HTTPError, RuntimeError, OSError) as exc:
        raise HTTPException(503, f"Voce non disponibile: {exc}")
    return Response(wav, media_type="audio/wav", headers=NO_CACHE)


# =========================================================================
# GESTIONE STRATEGIA MOTORE (Locale / ElevenLabs / Ibrido)
# =========================================================================

@admin_routes.get("/api/voices/engine")
async def admin_get_voice_engine(_: str = Depends(require_admin)):
    mode = env_get("NUXIVA_VOICE_ENGINE_MODE", "hybrid").lower()
    eleven_voice = env_get("NUXIVA_ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    fallback_local = env_get("NUXIVA_VOICE_LOCAL_FALLBACK", "if_sara")
    has_key = bool(env_get("NUXIVA_ELEVENLABS_API_KEY", "").strip())
    return {
        "engine_mode": mode,
        "elevenlabs_voice_id": eleven_voice,
        "fallback_local": fallback_local,
        "elevenlabs_configured": has_key,
        "speed": float(env_get("NUXIVA_VOICE_SPEED", "1.0")),
        "pitch": float(env_get("NUXIVA_VOICE_PITCH", "0.0")),
        "volume": float(env_get("NUXIVA_VOICE_VOLUME", "1.0")),
        "stability": float(env_get("NUXIVA_ELEVENLABS_STABILITY", "0.65")),
        "similarity_boost": float(env_get("NUXIVA_ELEVENLABS_SIMILARITY_BOOST", "0.75")),
    }


@admin_routes.put("/api/voices/engine")
async def admin_set_voice_engine(request: Request, user: str = Depends(require_admin)):
    body = await request.json()
    updates = {}
    if "engine_mode" in body:
        m = str(body["engine_mode"]).lower()
        if m in ("local", "elevenlabs", "hybrid"):
            updates["NUXIVA_VOICE_ENGINE_MODE"] = m
    if "elevenlabs_voice_id" in body:
        updates["NUXIVA_ELEVENLABS_VOICE_ID"] = str(body["elevenlabs_voice_id"]).strip()
    if "fallback_local" in body:
        updates["NUXIVA_VOICE_LOCAL_FALLBACK"] = str(body["fallback_local"]).strip()
    if "speed" in body:
        updates["NUXIVA_VOICE_SPEED"] = str(round(float(body["speed"]), 2))
    if "pitch" in body:
        updates["NUXIVA_VOICE_PITCH"] = str(round(float(body["pitch"]), 1))
    if "volume" in body:
        updates["NUXIVA_VOICE_VOLUME"] = str(round(float(body["volume"]), 2))
    if "stability" in body:
        updates["NUXIVA_ELEVENLABS_STABILITY"] = str(round(float(body["stability"]), 2))
    if "similarity_boost" in body:
        updates["NUXIVA_ELEVENLABS_SIMILARITY_BOOST"] = str(round(float(body["similarity_boost"]), 2))

    if updates:
        write_env(updates)
        store.event("INFO", f"Configurazione motore vocale aggiornata da {user}", "voice")
    return await admin_get_voice_engine()


# =========================================================================
# GESTIONE ELEVENLABS (Stato Account, Voci, Chiave)
# =========================================================================

@admin_routes.get("/api/voices/elevenlabs/status")
async def admin_elevenlabs_status(_: str = Depends(require_admin)):
    return await asyncio.to_thread(elevenlabs_client.get_subscription_info)


@admin_routes.post("/api/voices/elevenlabs/key")
async def admin_elevenlabs_set_key(request: Request, user: str = Depends(require_admin)):
    body = await request.json()
    api_key = str(body.get("api_key", "")).strip()
    if not api_key:
        raise HTTPException(400, "Chiave API mancante")

    # Verifica validità della chiave
    info = await asyncio.to_thread(elevenlabs_client.get_subscription_info, api_key)
    if info.get("status") == "error":
        raise HTTPException(400, f"Chiave ElevenLabs non valida: {info.get('message', 'Errore')}")

    write_env({"NUXIVA_ELEVENLABS_API_KEY": api_key})
    store.event("INFO", f"Nuova chiave ElevenLabs impostata da {user} (Piano: {info.get('tier')})", "voice")
    return {"ok": True, "subscription": info}


@admin_routes.get("/api/voices/elevenlabs/voices")
async def admin_elevenlabs_voices(_: str = Depends(require_admin)):
    voices_list = await asyncio.to_thread(elevenlabs_client.get_voices)
    return {"voices": voices_list}


@admin_routes.post("/api/voices/elevenlabs/test")
async def admin_elevenlabs_test(request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    text = str(body.get("text", "Ciao, questa è una prova vocale con ElevenLabs per Nuxiva.")).strip()
    voice_id = str(body.get("voice_id", "21m00Tcm4TlvDq8ikWAM")).strip()
    try:
        wav = await asyncio.to_thread(elevenlabs_client.synthesize, text, voice_id)
    except Exception as exc:
        raise HTTPException(502, f"Errore sintesi ElevenLabs: {exc}")
    return Response(wav, media_type="audio/wav", headers=NO_CACHE)


# =========================================================================
# CASSAFORTE AUDIO & RISPARMIO CREDITI/TOKEN (Audio Vault)
# =========================================================================

@admin_routes.get("/api/voices/vault/stats")
async def admin_vault_stats(_: str = Depends(require_admin)):
    return audio_vault.get_stats()


@admin_routes.get("/api/voices/vault/clips")
async def admin_vault_clips(q: str = "", limit: int = 50, _: str = Depends(require_admin)):
    return {"clips": audio_vault.list_clips(query=q, limit=limit)}


@admin_routes.get("/api/voices/vault/clips/{clip_id}/audio")
async def admin_vault_clip_audio(clip_id: str, _: str = Depends(require_admin)):
    audio_bytes = audio_vault.get_clip_audio(clip_id)
    if not audio_bytes:
        raise HTTPException(404, "Audio clip non trovata")
    return Response(audio_bytes, media_type="audio/wav", headers=NO_CACHE)


@admin_routes.delete("/api/voices/vault/clips/{clip_id}")
async def admin_vault_delete_clip(clip_id: str, _: str = Depends(require_admin)):
    ok = audio_vault.delete_clip(clip_id)
    if not ok:
        raise HTTPException(404, "Clip non trovata")
    return {"ok": True}


@admin_routes.post("/api/voices/vault/pregenerate")
async def admin_vault_pregenerate(request: Request, user: str = Depends(require_admin)):
    """Pre-genera le frasi tattiche e domotiche frequenti salvandole in cassaforte."""
    body = await request.json() if request.headers.get("content-length") else {}
    target_voice = str(body.get("voice", "")).strip() or None
    created = 0
    for item in COMMON_PHRASES:
        txt = item["text"]
        try:
            wav = await synthesis.synthesize(txt, voice=target_voice)
            audio_vault.store(txt, target_voice or "default", "pregenerated", wav, pinned=True)
            created += 1
        except Exception as exc:
            logger.warning("Errore pre-generazione frase '%s': %s", txt, exc)
    store.event("INFO", f"Pre-generate {created} frasi audio in cassaforte da {user}", "voice")
    return {"ok": True, "created_count": created, "stats": audio_vault.get_stats()}


@admin_routes.post("/api/voices/vault/clear")
async def admin_vault_clear(_: str = Depends(require_admin)):
    deleted = audio_vault.clear_unpinned()
    return {"ok": True, "deleted_count": deleted, "stats": audio_vault.get_stats()}
