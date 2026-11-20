"""Cassaforte Audio e Risparmio Crediti/Token per Nuxiva.

Salva in modo persistente le sintesi vocali riutilizzabili per evitare
chiamate ridondanti ad ElevenLabs (risparmiando crediti del piano free/paid)
e riducendo la latenza a zero (< 5ms da disco locale).
"""

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nuxiva.voices.vault")

# Directory di memorizzazione
from config import STATE_DIR

def _resolve_vault_dir() -> Path:
    target = Path(STATE_DIR) / "audio_vault"
    try:
        target.mkdir(parents=True, exist_ok=True)
        return target
    except OSError:
        fallback = Path("/tmp/nuxiva_audio_vault")
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback

VAULT_DIR = _resolve_vault_dir()
INDEX_FILE = VAULT_DIR / "vault_index.json"

# Frasi standard frequenti che possono essere pre-generate in 1 click
COMMON_PHRASES = [
    {"category": "saluti", "text": "Buongiorno, tutti i sistemi di Nuxiva sono pronti e operativi."},
    {"category": "saluti", "text": "Buonasera, monitoraggio attivo."},
    {"category": "saluti", "text": "Buonanotte, attivo la sorveglianza notturna silenziosa."},
    {"category": "conferme", "text": "Comando eseguito con successo."},
    {"category": "conferme", "text": "Ricevuto, procedo subito."},
    {"category": "conferme", "text": "Fatto, operazione completata."},
    {"category": "domotica", "text": "Luce accesa."},
    {"category": "domotica", "text": "Luce spenta."},
    {"category": "domotica", "text": "Temperatura impostata a ventuno gradi."},
    {"category": "domotica", "text": "Dispositivo scollegato dalla rete."},
    {"category": "sicurezza", "text": "Attenzione: movimento rilevato nell'area perimetrale."},
    {"category": "sicurezza", "text": "Tutti i varchi e le telecamere sono in stato sicuro."},
    {"category": "stato", "text": "Nessuna anomalia riscontrata nei registri di sistema."},
    {"category": "stato", "text": "La connessione internet è stabile e funzionante."},
]


def _ensure_vault():
    try:
        VAULT_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    if not INDEX_FILE.exists():
        initial = {
            "version": 1,
            "total_hits": 0,
            "total_chars_saved": 0,
            "clips": {},
        }
        try:
            INDEX_FILE.write_text(json.dumps(initial, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass


def _read_index() -> Dict[str, Any]:
    _ensure_vault()
    try:
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Errore lettura indice Audio Vault: %s", exc)
        return {"version": 1, "total_hits": 0, "total_chars_saved": 0, "clips": {}}


def _write_index(index: Dict[str, Any]) -> None:
    _ensure_vault()
    tmp_path = VAULT_DIR / "vault_index.json.tmp"
    tmp_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_path.replace(INDEX_FILE)


def compute_clip_id(text: str, voice_id: str, engine: str) -> str:
    norm_text = text.strip().lower()
    norm_voice = voice_id.strip()
    norm_engine = engine.strip().lower()
    raw = f"{norm_engine}|{norm_voice}|{norm_text}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:16]


class AudioVault:
    def __init__(self):
        _ensure_vault()

    def lookup(self, text: str, voice_id: str, engine: str) -> Optional[bytes]:
        """Cerca l'audio nella cassaforte. Se trovato, incrementa statistiche e restituisce i byte WAV."""
        clip_id = compute_clip_id(text, voice_id, engine)
        audio_path = VAULT_DIR / f"{clip_id}.wav"
        if not audio_path.exists():
            return None

        try:
            audio_bytes = audio_path.read_bytes()
            # Aggiornamento contatori
            index = _read_index()
            clips = index.setdefault("clips", {})
            char_count = len(text.strip())

            index["total_hits"] = index.get("total_hits", 0) + 1
            index["total_chars_saved"] = index.get("total_chars_saved", 0) + char_count

            if clip_id in clips:
                clips[clip_id]["hit_count"] = clips[clip_id].get("hit_count", 0) + 1
                clips[clip_id]["last_used_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                clips[clip_id]["chars_saved"] = clips[clip_id].get("chars_saved", 0) + char_count
            else:
                clips[clip_id] = {
                    "id": clip_id,
                    "text": text,
                    "voice_id": voice_id,
                    "engine": engine,
                    "char_count": char_count,
                    "hit_count": 1,
                    "chars_saved": char_count,
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "last_used_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "pinned": False,
                }
            _write_index(index)
            logger.info("Audio Vault HIT: clip '%s' riutilizzata! Crediti risparmiati: %d", clip_id, char_count)
            return audio_bytes
        except Exception as exc:
            logger.warning("Errore lettura clip %s: %s", clip_id, exc)
            return None

    def store(self, text: str, voice_id: str, engine: str, audio_bytes: bytes, pinned: bool = False) -> str:
        """Salva una sintesi audio nella cassaforte."""
        if not audio_bytes or len(audio_bytes) < 100:
            return ""

        clip_id = compute_clip_id(text, voice_id, engine)
        audio_path = VAULT_DIR / f"{clip_id}.wav"

        try:
            audio_path.write_bytes(audio_bytes)
            index = _read_index()
            clips = index.setdefault("clips", {})
            now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            if clip_id not in clips:
                clips[clip_id] = {
                    "id": clip_id,
                    "text": text,
                    "voice_id": voice_id,
                    "engine": engine,
                    "char_count": len(text.strip()),
                    "hit_count": 0,
                    "chars_saved": 0,
                    "created_at": now,
                    "last_used_at": now,
                    "pinned": pinned,
                    "file_size": len(audio_bytes),
                }
            else:
                if pinned:
                    clips[clip_id]["pinned"] = True
                clips[clip_id]["file_size"] = len(audio_bytes)

            _write_index(index)
            return clip_id
        except Exception as exc:
            logger.warning("Impossibile salvare in Audio Vault (%s): %s", clip_id, exc)
            return ""

    def get_stats(self) -> Dict[str, Any]:
        """Restituisce le statistiche generali di risparmio."""
        index = _read_index()
        clips = index.get("clips", {})
        total_clips = len(clips)
        total_hits = index.get("total_hits", 0)
        total_chars_saved = index.get("total_chars_saved", 0)

        # Calcolo dimensione su disco
        total_bytes = 0
        for p in VAULT_DIR.glob("*.wav"):
            try:
                total_bytes += p.stat().st_size
            except OSError:
                pass

        # Stima crediti ElevenLabs gratuiti preservati (in % su piano base da 10k)
        equiv_free_plans = round(total_chars_saved / 10000.0, 2)

        return {
            "total_clips": total_clips,
            "total_hits": total_hits,
            "total_chars_saved": total_chars_saved,
            "equivalent_free_plans_saved": equiv_free_plans,
            "total_size_mb": round(total_bytes / (1024 * 1024), 2),
            "common_phrases_count": len(COMMON_PHRASES),
        }

    def list_clips(self, query: str = "", limit: int = 60) -> List[Dict[str, Any]]:
        """Restituisce l'elenco delle clip con filtri per la UI."""
        index = _read_index()
        clips = list(index.get("clips", {}).values())
        needle = query.strip().lower()
        if needle:
            clips = [c for c in clips if needle in c.get("text", "").lower() or needle in c.get("voice_id", "").lower()]

        # Ordina prima per numero di riutilizzi (più utili in alto), poi data
        clips.sort(key=lambda c: (c.get("hit_count", 0), c.get("last_used_at", "")), reverse=True)
        return clips[:limit]

    def get_clip_audio(self, clip_id: str) -> Optional[bytes]:
        """Restituisce i byte audio della clip richiesta per anteprima."""
        audio_path = VAULT_DIR / f"{clip_id}.wav"
        if audio_path.exists():
            return audio_path.read_bytes()
        return None

    def delete_clip(self, clip_id: str) -> bool:
        """Elimina una clip specifica."""
        audio_path = VAULT_DIR / f"{clip_id}.wav"
        audio_path.unlink(missing_ok=True)
        index = _read_index()
        if clip_id in index.get("clips", {}):
            del index["clips"][clip_id]
            _write_index(index)
            return True
        return False

    def clear_unpinned(self) -> int:
        """Svuota le clip non fissate."""
        index = _read_index()
        clips = index.get("clips", {})
        to_delete = [cid for cid, c in clips.items() if not c.get("pinned", False)]
        deleted_count = 0
        for cid in to_delete:
            (VAULT_DIR / f"{cid}.wav").unlink(missing_ok=True)
            del clips[cid]
            deleted_count += 1
        _write_index(index)
        return deleted_count


audio_vault = AudioVault()
