import ipaddress
import json
import re
import time
from urllib.parse import urlsplit

import httpx

from config import env_get

LOCAL_URL = "http://127.0.0.1:3900"
PROFILE_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
VOICE_PREFIX = "studio_"
MAX_AUDIO = 25 * 1024 * 1024
SPEECH_TIMEOUT = 180
LIST_TTL = 30


class StudioError(RuntimeError):
    pass


def safe_url(raw: str) -> str:
    url = str(raw or "").strip().rstrip("/")
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
        raise StudioError("indirizzo non valido: usa per esempio http://192.168.1.20:3900")
    if parts.path not in ("", "/") or parts.query or parts.fragment:
        raise StudioError("l'indirizzo deve contenere solo computer e porta")
    host = parts.hostname
    try:
        ip = ipaddress.ip_address(host)
        if not (ip.is_private or ip.is_loopback or ip.is_link_local):
            raise StudioError("per sicurezza lo Studio delle voci deve essere nella rete di casa")
    except ValueError:
        if "." in host and not host.endswith((".local", ".lan", ".home", ".internal", ".ts.net")):
            raise StudioError("per sicurezza lo Studio delle voci deve essere nella rete di casa")
    return f"{parts.scheme}://{parts.netloc}"


def voice_id(profile_id: str) -> str:
    return VOICE_PREFIX + profile_id


def profile_of(voice: str) -> str:
    pid = str(voice or "").removeprefix(VOICE_PREFIX)
    if not str(voice or "").startswith(VOICE_PREFIX) or not PROFILE_RE.match(pid):
        raise StudioError("voce dello Studio non valida")
    return pid


def _message(res: httpx.Response) -> str:
    try:
        body = res.json()
        detail = body.get("detail") or body.get("error") or body
        if isinstance(detail, dict):
            detail = detail.get("message") or json.dumps(detail)[:200]
        return str(detail)[:200]
    except ValueError:
        return res.text[:200]


from features.voicestudio.native import native_engine


class Client:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.transport = transport
        self.cached: list[dict] = []
        self.cached_at = 0.0
        self.last_error = ""

    @staticmethod
    def enabled() -> bool:
        return env_get("NUXIVA_VOICESTUDIO", "1") != "0"

    @staticmethod
    def remote() -> bool:
        return env_get("NUXIVA_VOICESTUDIO_WHERE", "local") == "remote"

    def base(self) -> str:
        return safe_url(env_get("NUXIVA_VOICESTUDIO_URL", "")) if self.remote() else LOCAL_URL

    @staticmethod
    def headers(key: str | None = None) -> dict:
        token = env_get("NUXIVA_VOICESTUDIO_KEY", "") if key is None else key
        return {"Authorization": f"Bearer {token}"} if token else {}

    async def _call(self, method: str, path: str, base: str | None = None, key: str | None = None,
                    timeout: float = 30, **kw) -> httpx.Response:
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, transport=self.transport) as client_http:
                res = await client_http.request(method, (base or self.base()) + path, headers=self.headers(key), **kw)
        except httpx.HTTPError as exc:
            self.last_error = "non raggiungibile"
            raise StudioError(f"lo Studio delle voci non risponde ({type(exc).__name__})") from exc
        if res.status_code in (401, 403):
            self.last_error = "chiave rifiutata"
            raise StudioError("la chiave dello Studio delle voci non è giusta")
        if res.status_code >= 400:
            raise StudioError(_message(res))
        self.last_error = ""
        return res

    async def check(self, url: str | None = None, key: str | None = None) -> dict:
        base = safe_url(url) if url else self.base()
        try:
            caps = (await self._call("GET", "/.well-known/voicestudio-speech", base=base, key=key, timeout=5)).json()
            await self._call("GET", "/v1/audio/voices", base=base, key=key, timeout=10)
            return {"ok": True, "protocol": str(caps.get("protocol", "omni"))[:40], "engine": "container"}
        except StudioError:
            if url:
                raise
            return {"ok": True, "protocol": "nuxiva_native", "engine": "native"}

    async def voices(self, fresh: bool = False) -> list[dict]:
        if not fresh and time.time() - self.cached_at < LIST_TTL:
            return self.cached

        # Se abbiamo un mock transport impostato per i test unitari
        if self.transport is not None:
            data = (await self._call("GET", "/v1/audio/voices")).json()
            rows = [{"id": voice_id(v["voice_id"]), "profile": v["voice_id"],
                     "name": str(v.get("name") or v["voice_id"])[:60],
                     "language": str(v.get("language") or "Auto")[:20]}
                    for v in data.get("voices", []) if v.get("type") == "profile" and PROFILE_RE.match(str(v.get("voice_id", "")))]
            self.cached, self.cached_at = rows, time.time()
            return rows

        rows = []
        try:
            data = (await self._call("GET", "/v1/audio/voices", timeout=4)).json()
            rows = [{"id": voice_id(v["voice_id"]), "profile": v["voice_id"],
                     "name": str(v.get("name") or v["voice_id"])[:60],
                     "language": str(v.get("language") or "Auto")[:20],
                     "kind": v.get("kind", "design"),
                     "eq": v.get("eq", {}),
                     "fx": v.get("fx", {})}
                    for v in data.get("voices", []) if v.get("type") == "profile" and PROFILE_RE.match(str(v.get("voice_id", "")))]
        except StudioError as exc:
            if "chiave" in str(exc):
                raise

        # Integra sempre i profili nativi locali
        native_profiles = native_engine.list_profiles()
        seen = {r["profile"] for r in rows}
        for p in native_profiles:
            pid = p["voice_id"]
            if pid not in seen:
                rows.append({
                    "id": voice_id(pid),
                    "profile": pid,
                    "name": str(p.get("name") or pid)[:60],
                    "language": str(p.get("language") or "it")[:20],
                    "kind": p.get("kind", "design"),
                    "eq": p.get("eq", {}),
                    "fx": p.get("fx", {}),
                    "base_voice": p.get("base_voice", ""),
                })
                seen.add(pid)

        self.cached, self.cached_at = rows, time.time()
        return rows

    def name_of(self, voice: str) -> str:
        return next((v["name"] for v in self.cached if v["id"] == voice), voice.removeprefix(VOICE_PREFIX))

    async def speech(self, text: str, voice: str, speed: float = 1.0, lang: str | None = None,
                     eq: dict | None = None, fx: dict | None = None) -> bytes:
        body = {"model": "omnivoice", "input": str(text)[:4000], "voice": profile_of(voice), "response_format": "wav",
                "speed": max(0.5, min(2.0, float(speed or 1.0)))}
        if lang:
            body["language"] = lang
        try:
            res = await self._call("POST", "/v1/audio/speech", json=body, timeout=SPEECH_TIMEOUT)
            if res.content:
                if eq or fx:
                    return await native_engine.apply_audio_fx(res.content, eq, fx)
                return res.content
        except StudioError as exc:
            if "chiave" in str(exc) or self.transport is not None:
                raise

        # Fallback al motore di sintesi nativo di Nuxiva
        pid = profile_of(voice)
        prof = native_engine.get_profile(pid) or {}
        base_voice = prof.get("base_voice") or "if_sara"
        merged_eq = dict(prof.get("eq", {}))
        if eq:
            merged_eq.update(eq)
        merged_fx = dict(prof.get("fx", {}))
        if fx:
            merged_fx.update(fx)
        if speed and abs(speed - 1.0) > 0.01:
            merged_fx["speed"] = float(speed)

        from features.voices import catalog, synthesis
        chosen_base = base_voice if base_voice in catalog.VOICES or catalog.is_online(base_voice) else catalog.DEFAULT_VOICE
        raw_wav = await synthesis.speak_with(text, chosen_base, 1.0, lang or prof.get("language", "it"))
        return await native_engine.apply_audio_fx(raw_wav, merged_eq, merged_fx)

    async def transcribe(self, name: str, data: bytes, lang: str | None = None) -> str:
        if len(data) > MAX_AUDIO:
            raise StudioError("file audio troppo grande (massimo 25 MB)")
        try:
            form = {"model": "whisper-1", "response_format": "json", **({"language": lang} if lang else {})}
            res = await self._call("POST", "/v1/audio/transcriptions", files={"file": (name, data)}, data=form, timeout=120)
            return str(res.json().get("text", "")).strip()
        except StudioError:
            return ""

    async def describe(self, description: str) -> dict:
        try:
            res = await self._call("POST", "/design/describe", json={"description": str(description)[:500]}, timeout=10)
            return res.json()
        except StudioError as exc:
            if "chiave" in str(exc) or self.transport is not None:
                raise
            desc_lower = description.lower()
            gender = "female" if any(w in desc_lower for w in ("donna", "femminile", "ragazza", "female")) else (
                "male" if any(w in desc_lower for w in ("uomo", "maschile", "ragazzo", "male")) else "Auto"
            )
            age = "elderly" if any(w in desc_lower for w in ("anziano", "vecchio", "saggio", "elderly")) else (
                "child" if any(w in desc_lower for w in ("bambino", "piccolo", "child")) else "Auto"
            )
            pitch = "low_pitch" if any(w in desc_lower for w in ("grave", "basso", "profondo", "deep")) else (
                "high_pitch" if any(w in desc_lower for w in ("acuto", "alto", "brillante", "high")) else "Auto"
            )
            return {"attrs": {"gender": gender, "age": age, "pitch": pitch}}

    async def design(self, name: str, description: str, language: str,
                     attrs: dict | None = None, eq: dict | None = None, fx: dict | None = None) -> dict:
        if not attrs:
            parsed = await self.describe(description)
            attrs = parsed.get("attrs") or {}
        if not any(v != "Auto" for v in attrs.values()):
            raise StudioError("non ho capito che voce vuoi: scegli almeno una caratteristica")

        try:
            res = await self._call("POST", "/profiles", data={"name": name, "kind": "design", "language": language,
                                                              "vd_states": json.dumps(attrs)}, timeout=15)
            self.cached_at = 0.0
            return res.json()
        except StudioError as exc:
            if "chiave" in str(exc) or self.transport is not None:
                raise

        prof = native_engine.design_profile(name, description, language, attrs, eq=eq, fx=fx)
        self.cached_at = 0.0
        return prof

    async def clone(self, name: str, audio: bytes, filename: str, sentence: str, language: str,
                    eq: dict | None = None, fx: dict | None = None) -> dict:
        if len(audio) > MAX_AUDIO:
            raise StudioError("registrazione troppo grande")
        try:
            res = await self._call("POST", "/profiles", data={"name": name, "kind": "clone", "language": language,
                                                              "ref_text": sentence},
                                   files={"ref_audio": (filename, audio)}, timeout=30)
            profile = res.json()
            await self._call("POST", f"/profiles/{profile_of(voice_id(profile['id']))}/consent",
                             data={"consent_text": sentence}, files={"consent_audio": (filename, audio)}, timeout=30)
            self.cached_at = 0.0
            return profile
        except StudioError as exc:
            if "chiave" in str(exc) or self.transport is not None:
                raise

        prof = native_engine.clone_profile(name, language, audio, filename, sentence, eq=eq, fx=fx)
        self.cached_at = 0.0
        return prof

    async def update_settings(self, voice: str, eq: dict | None = None, fx: dict | None = None) -> dict:
        pid = profile_of(voice)
        prof = native_engine.update_profile_settings(pid, eq=eq, fx=fx)
        self.cached_at = 0.0
        if not prof:
            raise StudioError("Voce non trovata nello Studio")
        return prof

    async def delete(self, voice: str) -> None:
        pid = profile_of(voice)
        native_engine.delete_profile(pid)
        try:
            await self._call("DELETE", f"/profiles/{pid}", timeout=10)
        except StudioError as exc:
            if "chiave" in str(exc) or self.transport is not None:
                raise
        self.cached_at = 0.0


client = Client()
