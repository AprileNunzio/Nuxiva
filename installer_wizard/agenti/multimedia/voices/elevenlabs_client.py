"""Client di integrazione ElevenLabs per Nuxiva.

Supporta:
- Verifica API Key e lettura stato abbonamento (incluso Free Tier 10.000 caratteri)
- Elenco voci disponibili (premade, clonate, personali)
- Sintesi vocale con gestione quote, streaming e riconversione WAV standard
"""

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nuxiva.voices.elevenlabs")

BASE_URL = "https://api.elevenlabs.io/v1"
DEFAULT_MODEL = "eleven_multilingual_v2"


class ElevenLabsError(RuntimeError):
    """Errore generico API ElevenLabs."""
    pass


class ElevenLabsQuotaError(ElevenLabsError):
    """Quota o crediti mensili ElevenLabs esauriti."""
    pass


def _get_api_key(explicit_key: Optional[str] = None) -> str:
    key = (explicit_key or os.environ.get("NUXIVA_ELEVENLABS_API_KEY", "")).strip()
    return key


def _make_request(
    endpoint: str,
    method: str = "GET",
    payload: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    timeout: float = 30.0,
) -> bytes:
    key = _get_api_key(api_key)
    if not key:
        raise ElevenLabsError("Chiave API ElevenLabs non configurata")

    url = f"{BASE_URL}{endpoint}"
    data = json.dumps(payload).encode("utf-8") if payload else None
    headers = {
        "xi-api-key": key,
        "Accept": "application/json",
        "User-Agent": "NuxivaOS/5.8",
    }
    if payload:
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        err_msg = ""
        try:
            raw_err = exc.read().decode("utf-8", errors="ignore")
            parsed = json.loads(raw_err)
            detail = parsed.get("detail", {})
            err_msg = detail.get("message") if isinstance(detail, dict) else str(detail or raw_err)
        except Exception:
            err_msg = str(exc)

        if exc.code == 401:
            raise ElevenLabsError("Chiave API ElevenLabs non valida o revocata") from exc
        if exc.code == 429 or "quota" in err_msg.lower() or "character limit" in err_msg.lower():
            raise ElevenLabsQuotaError(f"Crediti ElevenLabs esauriti per questo mese: {err_msg}") from exc
        raise ElevenLabsError(f"Errore ElevenLabs ({exc.code}): {err_msg}") from exc
    except Exception as exc:
        raise ElevenLabsError(f"Impossibile raggiungere i server ElevenLabs: {exc}") from exc


def get_subscription_info(api_key: Optional[str] = None) -> Dict[str, Any]:
    """Interroga lo stato dell'abbonamento e i crediti residui."""
    key = _get_api_key(api_key)
    if not key:
        return {
            "configured": False,
            "tier": "none",
            "character_count": 0,
            "character_limit": 0,
            "remaining_characters": 0,
            "percent_used": 0.0,
            "next_reset_days": 0,
            "status": "unconfigured",
            "message": "Nessuna chiave configurata",
        }

    try:
        raw = _make_request("/user/subscription", method="GET", api_key=key, timeout=15.0)
        data = json.loads(raw.decode("utf-8"))
        tier = data.get("tier", "free")
        char_count = int(data.get("character_count", 0))
        char_limit = int(data.get("character_limit", 10000))
        remaining = max(0, char_limit - char_count)
        percent = round((char_count / max(char_limit, 1)) * 100, 1)
        next_invoice = data.get("next_invoice") or {}
        next_reset_ts = next_invoice.get("next_payment_attempt", 0)

        import time
        days_to_reset = max(0, int((next_reset_ts - time.time()) / 86400)) if next_reset_ts > time.time() else 30

        return {
            "configured": True,
            "tier": tier,
            "character_count": char_count,
            "character_limit": char_limit,
            "remaining_characters": remaining,
            "percent_used": percent,
            "next_reset_days": days_to_reset,
            "status": data.get("status", "active"),
            "can_extend": data.get("can_extend_character_limit", False),
            "allowed_to_use": data.get("allowed_to_use_instant_voice_cloning", False),
        }
    except ElevenLabsError as exc:
        return {
            "configured": True,
            "tier": "error",
            "character_count": 0,
            "character_limit": 0,
            "remaining_characters": 0,
            "percent_used": 0.0,
            "next_reset_days": 0,
            "status": "error",
            "message": str(exc),
        }


def get_voices(api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """Elenco di tutte le voci disponibili per l'account (premade e clonate)."""
    key = _get_api_key(api_key)
    if not key:
        return []

    try:
        raw = _make_request("/voices", method="GET", api_key=key, timeout=20.0)
        data = json.loads(raw.decode("utf-8"))
        voices_list = data.get("voices", [])
        result = []
        for v in voices_list:
            labels = v.get("labels") or {}
            result.append({
                "id": v.get("voice_id", ""),
                "name": v.get("name", "Sconosciuta"),
                "category": v.get("category", "premade"),
                "preview_url": v.get("preview_url", ""),
                "gender": labels.get("gender", ""),
                "accent": labels.get("accent", ""),
                "description": labels.get("description") or labels.get("use case", ""),
                "high_quality": v.get("high_quality_base_model_ids", []),
            })
        return result
    except Exception as exc:
        logger.warning("Errore nel recupero voci ElevenLabs: %s", exc)
        return []


def synthesize(
    text: str,
    voice_id: str,
    model_id: str = DEFAULT_MODEL,
    stability: float = 0.50,
    similarity_boost: float = 0.75,
    style: float = 0.0,
    api_key: Optional[str] = None,
) -> bytes:
    """Sintetizza l'audio tramite ElevenLabs API v1."""
    key = _get_api_key(api_key)
    if not key:
        raise ElevenLabsError("Chiave API ElevenLabs non impostata")

    endpoint = f"/text-to-speech/{voice_id}?output_format=mp3_44100_128"
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": round(max(0.0, min(1.0, stability)), 2),
            "similarity_boost": round(max(0.0, min(1.0, similarity_boost)), 2),
            "style": round(max(0.0, min(1.0, style)), 2),
            "use_speaker_boost": True,
        },
    }

    url = f"{BASE_URL}{endpoint}"
    req_data = json.dumps(payload).encode("utf-8")
    headers = {
        "xi-api-key": key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
        "User-Agent": "NuxivaOS/5.8",
    }

    req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=40.0) as resp:
            audio_data = resp.read()
    except urllib.error.HTTPError as exc:
        raw_err = exc.read().decode("utf-8", errors="ignore")
        if exc.code == 429 or "quota" in raw_err.lower() or "character" in raw_err.lower():
            raise ElevenLabsQuotaError(f"Limite caratteri ElevenLabs superato: {raw_err}") from exc
        raise ElevenLabsError(f"Errore generazione voce ElevenLabs ({exc.code}): {raw_err}") from exc
    except Exception as exc:
        raise ElevenLabsError(f"Errore connessione ElevenLabs: {exc}") from exc

    # Conversione in WAV PCM standard tramite ffmpeg per uniformità con il resto di Nuxiva
    import subprocess
    try:
        proc = subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-ac", "1", "-ar", "24000", "-f", "wav", "pipe:1"],
            input=audio_data,
            capture_output=True,
            timeout=15,
        )
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout
    except Exception as exc:
        logger.warning("Conversione ffmpeg non riuscita (%s), ritorno MP3 originale", exc)

    return audio_data
