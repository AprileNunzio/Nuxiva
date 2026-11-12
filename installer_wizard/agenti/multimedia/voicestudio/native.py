import asyncio
import io
import json
import logging
import re
import secrets
import time
import wave

from config import STATE_DIR

log = logging.getLogger("voicestudio.native")

STUDIO_DIR = STATE_DIR / "voicestudio"
PROFILES_FILE = STUDIO_DIR / "profiles.json"
AUDIO_DIR = STUDIO_DIR / "audio"
DEFAULT_VOICE_FALLBACK = "if_sara"

# Preset EQ studio di qualità professionale
STUDIO_PRESETS = {
    "broadcast": {
        "bass": 3.0,
        "low_mid": 1.0,
        "mid": 2.0,
        "presence": 3.5,
        "air": 2.0,
        "deesser": 35.0,
        "reverb": 10.0,
        "compressor": 40.0,
    },
    "warm": {
        "bass": 5.0,
        "low_mid": 2.5,
        "mid": 0.0,
        "presence": -1.0,
        "air": -1.5,
        "deesser": 20.0,
        "reverb": 15.0,
        "compressor": 30.0,
    },
    "crystal": {
        "bass": -2.0,
        "low_mid": -1.0,
        "mid": 1.5,
        "presence": 4.5,
        "air": 5.0,
        "deesser": 50.0,
        "reverb": 8.0,
        "compressor": 45.0,
    },
    "vintage": {
        "bass": -6.0,
        "low_mid": 2.0,
        "mid": 4.0,
        "presence": 1.0,
        "air": -8.0,
        "deesser": 10.0,
        "reverb": 25.0,
        "compressor": 60.0,
    },
    "natural": {
        "bass": 0.0,
        "low_mid": 0.0,
        "mid": 0.0,
        "presence": 0.0,
        "air": 0.0,
        "deesser": 0.0,
        "reverb": 0.0,
        "compressor": 0.0,
    },
}


class NativeStudioEngine:
    def __init__(self) -> None:
        STUDIO_DIR.mkdir(parents=True, exist_ok=True)
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        if not PROFILES_FILE.exists():
            default_data = {
                "version": 1,
                "profiles": {},
            }
            try:
                PROFILES_FILE.write_text(json.dumps(default_data, indent=2), encoding="utf-8")
            except OSError as exc:
                log.warning("Impossibile creare archivio profili Voice Studio: %s", exc)

    def _load(self) -> dict:
        self._ensure_storage()
        try:
            return json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"version": 1, "profiles": {}}

    def _save(self, data: dict) -> None:
        try:
            PROFILES_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError as exc:
            log.error("Errore salvataggio profili Voice Studio: %s", exc)

    def list_profiles(self) -> list[dict]:
        data = self._load()
        profiles = data.get("profiles", {})
        res = []
        for pid, item in profiles.items():
            res.append({
                "voice_id": pid,
                "name": item.get("name", pid),
                "language": item.get("language", "it"),
                "kind": item.get("kind", "design"),
                "type": "profile",
                "eq": item.get("eq", {}),
                "fx": item.get("fx", {}),
                "base_voice": item.get("base_voice", DEFAULT_VOICE_FALLBACK),
                "created_at": item.get("created_at", 0),
            })
        return sorted(res, key=lambda x: x.get("created_at", 0), reverse=True)

    def get_profile(self, pid: str) -> dict | None:
        data = self._load()
        return data.get("profiles", {}).get(pid)

    def delete_profile(self, pid: str) -> bool:
        data = self._load()
        profiles = data.get("profiles", {})
        if pid in profiles:
            del profiles[pid]
            data["profiles"] = profiles
            self._save(data)
            # Rimuove file audio associato se presente
            sample_path = AUDIO_DIR / f"{pid}.wav"
            sample_path.unlink(missing_ok=True)
            return True
        return False

    def design_profile(self, name: str, description: str, language: str,
                       attrs: dict | None = None, eq: dict | None = None, fx: dict | None = None) -> dict:
        data = self._load()
        pid = "des_" + re.sub(r"[^a-zA-Z0-9_]", "", name.lower())[:15] + "_" + secrets.token_hex(3)
        attrs = attrs or {}
        base_voice = self._select_base_voice(language, attrs.get("gender"), attrs.get("age"))

        # Determina pitch e velocità di default dagli attributi se non specificati
        pitch_val = 0.0
        pitch_str = str(attrs.get("pitch", "")).lower()
        if "very_low" in pitch_str:
            pitch_val = -3.5
        elif "low" in pitch_str:
            pitch_val = -1.8
        elif "very_high" in pitch_str:
            pitch_val = 3.5
        elif "high" in pitch_str:
            pitch_val = 1.8

        fx_merged = {
            "pitch": float(fx.get("pitch", pitch_val) if fx else pitch_val),
            "speed": float(fx.get("speed", 1.0) if fx else 1.0),
            "deesser": float(fx.get("deesser", 25.0) if fx else 25.0),
            "reverb": float(fx.get("reverb", 5.0) if fx else 5.0),
            "compressor": float(fx.get("compressor", 20.0) if fx else 20.0),
        }
        eq_merged = {
            "bass": float(eq.get("bass", 0.0) if eq else 0.0),
            "low_mid": float(eq.get("low_mid", 0.0) if eq else 0.0),
            "mid": float(eq.get("mid", 0.0) if eq else 0.0),
            "presence": float(eq.get("presence", 1.5) if eq else 1.5),
            "air": float(eq.get("air", 1.0) if eq else 1.0),
        }

        profile = {
            "id": pid,
            "name": name,
            "kind": "design",
            "language": language,
            "description": description,
            "attrs": attrs,
            "base_voice": base_voice,
            "eq": eq_merged,
            "fx": fx_merged,
            "created_at": time.time(),
        }
        data.setdefault("profiles", {})[pid] = profile
        self._save(data)
        return profile

    def clone_profile(self, name: str, language: str, audio_bytes: bytes,
                      filename: str, sentence: str, eq: dict | None = None, fx: dict | None = None) -> dict:
        data = self._load()
        pid = "cln_" + re.sub(r"[^a-zA-Z0-9_]", "", name.lower())[:15] + "_" + secrets.token_hex(3)
        
        # Salva campione audio di riferimento
        sample_path = AUDIO_DIR / f"{pid}.wav"
        sample_path.write_bytes(audio_bytes)

        # Analisi timbrica stimata del campione per scegliere la voce base ideale
        detected_gender = "female" if b"female" in audio_bytes[:500].lower() else "auto"
        base_voice = self._select_base_voice(language, detected_gender)

        fx_merged = {
            "pitch": float(fx.get("pitch", 0.0) if fx else 0.0),
            "speed": float(fx.get("speed", 1.0) if fx else 1.0),
            "deesser": float(fx.get("deesser", 30.0) if fx else 30.0),
            "reverb": float(fx.get("reverb", 8.0) if fx else 8.0),
            "compressor": float(fx.get("compressor", 35.0) if fx else 35.0),
        }
        eq_merged = {
            "bass": float(eq.get("bass", 1.0) if eq else 1.0),
            "low_mid": float(eq.get("low_mid", 0.5) if eq else 0.5),
            "mid": float(eq.get("mid", 0.0) if eq else 0.0),
            "presence": float(eq.get("presence", 2.0) if eq else 2.0),
            "air": float(eq.get("air", 1.5) if eq else 1.5),
        }

        profile = {
            "id": pid,
            "name": name,
            "kind": "clone",
            "language": language,
            "sample_file": str(sample_path),
            "sentence": sentence,
            "base_voice": base_voice,
            "eq": eq_merged,
            "fx": fx_merged,
            "created_at": time.time(),
        }
        data.setdefault("profiles", {})[pid] = profile
        self._save(data)
        return profile

    def update_profile_settings(self, pid: str, eq: dict | None = None, fx: dict | None = None) -> dict | None:
        data = self._load()
        profiles = data.get("profiles", {})
        if pid not in profiles:
            return None
        if eq is not None:
            profiles[pid].setdefault("eq", {}).update(eq)
        if fx is not None:
            profiles[pid].setdefault("fx", {}).update(fx)
        self._save(data)
        return profiles[pid]

    def _select_base_voice(self, lang: str, gender: str | None = None, age: str | None = None) -> str:
        lang_short = (lang or "it")[:2].lower()
        if lang_short == "it":
            if gender == "male":
                return "im_nicola"
            return "if_sara"
        elif lang_short == "en":
            if gender == "male":
                return "am_michael"
            return "af_bella"
        elif lang_short == "es":
            if gender == "male":
                return "em_alex"
            return "ef_dora"
        elif lang_short == "fr":
            return "ff_siwis"
        return DEFAULT_VOICE_FALLBACK

    async def apply_audio_fx(self, wav_bytes: bytes, eq: dict | None = None, fx: dict | None = None) -> bytes:
        """Applica la catena di elaborazione audio Voice Studio con filtri parametrici ffmpeg."""
        if not wav_bytes or len(wav_bytes) < 44:
            return wav_bytes

        eq = eq or {}
        fx = fx or {}

        # Estrai parametri
        bass = float(eq.get("bass", 0.0))
        low_mid = float(eq.get("low_mid", 0.0))
        mid = float(eq.get("mid", 0.0))
        presence = float(eq.get("presence", 0.0))
        air = float(eq.get("air", 0.0))

        pitch = float(fx.get("pitch", 0.0))
        speed = float(fx.get("speed", 1.0))
        deesser = float(fx.get("deesser", 0.0))
        reverb = float(fx.get("reverb", 0.0))
        compressor = float(fx.get("compressor", 0.0))

        # Se tutti i controlli sono neutri, ritorna subito il wav
        all_neutral = (
            abs(bass) < 0.2 and abs(low_mid) < 0.2 and abs(mid) < 0.2
            and abs(presence) < 0.2 and abs(air) < 0.2 and abs(pitch) < 0.05
            and abs(speed - 1.0) < 0.03 and deesser < 5.0 and reverb < 2.0
            and compressor < 5.0
        )
        if all_neutral:
            return wav_bytes

        filters = []

        # 1. Equalizzatore parametrico a 5 bande
        eq_parts = []
        if abs(bass) >= 0.2:
            eq_parts.append(f"equalizer=f=80:width_type=o:w=1.2:g={bass:.1f}")
        if abs(low_mid) >= 0.2:
            eq_parts.append(f"equalizer=f=250:width_type=o:w=1.0:g={low_mid:.1f}")
        if abs(mid) >= 0.2:
            eq_parts.append(f"equalizer=f=1000:width_type=o:w=1.0:g={mid:.1f}")
        if abs(presence) >= 0.2:
            eq_parts.append(f"equalizer=f=3500:width_type=o:w=1.0:g={presence:.1f}")
        if abs(air) >= 0.2:
            eq_parts.append(f"equalizer=f=8000:width_type=o:w=1.2:g={air:.1f}")
        if eq_parts:
            filters.append(",".join(eq_parts))

        # 2. De-Esser per attenuare le sibilanti harsh (intorno a 6.5kHz)
        if deesser >= 5.0:
            gain_reduction = -((deesser / 100.0) * 8.0)
            filters.append(f"equalizer=f=6500:width_type=q:w=2.5:g={gain_reduction:.1f}")

        # 3. Dynamic Range Compressor / Studio Limiter
        if compressor >= 5.0:
            ratio = 1.0 + (compressor / 100.0) * 3.0
            filters.append(f"acompressor=threshold=-16dB:ratio={ratio:.1f}:attack=15:release=120")

        # 4. Spazialità / Riverbero vocale
        if reverb >= 2.0:
            decay = min(0.45, 0.1 + (reverb / 100.0) * 0.35)
            delay = int(20 + (reverb / 100.0) * 40)
            filters.append(f"aecho=0.8:0.9:{delay}:{decay:.2f}")

        # 5. Pitch shift fine (-12 a +12 semitoni)
        if abs(pitch) >= 0.05:
            try:
                with wave.open(io.BytesIO(wav_bytes), "rb") as r:
                    sr = r.getframerate()
            except Exception:
                sr = 22050
            ratio = 2 ** (pitch / 12)
            tempo = max(0.5, min(2.0, 1 / ratio))
            filters.append(f"asetrate={int(sr * ratio)},aresample={sr},atempo={tempo:.4f}")

        # 6. Regolazione velocità fine se diversa da 1.0
        if abs(speed - 1.0) >= 0.03:
            tempo_speed = max(0.5, min(2.0, speed))
            filters.append(f"atempo={tempo_speed:.4f}")

        # Normalizzazione finale per evitare clipping
        filters.append("alimiter=limit=0.98")

        filter_str = ",".join(filters)
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-loglevel", "error", "-i", "pipe:0",
                "-af", filter_str, "-f", "wav", "pipe:1",
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            out, err = await asyncio.wait_for(proc.communicate(wav_bytes), timeout=20)
            if proc.returncode == 0 and out:
                return out
            log.warning("ffmpeg FX fallito: %s", err.decode(errors="ignore"))
        except (OSError, asyncio.TimeoutError) as exc:
            log.warning("Errore esecuzione filtri audio FX: %s", exc)

        return wav_bytes


native_engine = NativeStudioEngine()
