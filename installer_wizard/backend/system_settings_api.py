import ipaddress
import json
import logging
import re
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from access import NO_CACHE, require_admin, require_display
from config import NUXIVA_DIR, env_get, read_env, write_env
from settings import normalize_ollama
from state import store

log = logging.getLogger("nuxiva.system_settings")

public_routes = APIRouter()
admin_routes = APIRouter()

_ollama_cache = {}

try:
    from agenti.brain.brains import brains
except ImportError:
    class _DummyBrains:
        def invalidate(self):
            pass
    brains = _DummyBrains()

SCREEN_ROLES = ("agent", "work", "visual")
SCREEN_KEYS = frozenset(str(n) for n in range(17))

DEFAULT_DISPLAY_SETTINGS = {
    "show_assistant_name": True,
    "show_clock": True,
    "show_date": True,
    "show_thinking": True,
    "show_dock": True,
    "show_mic": True,
    "show_telemetry_chips": True,
    "show_presence": True,
    "show_holo_avatar": True,
    "show_desk_widgets": True,
    "sound_effects": True,
    "mic_autocalibrate": True,
    "session_mode": "shared",
    "surfaces": {},
    "screen_roles": {},
}

SURFACE_DEFAULTS = {
    "rail_voice": False,
    "rail_home": True,
    "rail_scan": True,
    "rail_vitals": True,
    "rail_learned": True,
    "project": True,
    "music_clock": True,
    "brain_badge": True,
    "token_usage": False,
}


def _surfaces(value: object, base: dict | None = None) -> dict:
    merged = dict(SURFACE_DEFAULTS if base is None else base)
    if isinstance(value, dict):
        merged.update({k: v for k, v in value.items() if k in SURFACE_DEFAULTS and isinstance(v, bool)})
    return merged


def _screen_roles(value: object) -> dict:
    if not isinstance(value, dict):
        return {}
    out = {}
    for key, role in value.items():
        if isinstance(key, str) and key in SCREEN_KEYS and role in SCREEN_ROLES:
            out[key] = role
    return out


DEFAULT_BACKEND_SETTINGS = {
    "ollama_url": "",
    "active_llm_model": "",
    "fast_llm_model": "",
    "auto_shutdown_local_ollama": True,
    "mesh_broadcast": True,
    "mesh_state_sync": True,
    "process_watchdog": True,
    "verbose_telemetry": False,
}


def _nuxiva_dir():
    import sys
    sys_api = sys.modules.get("system_api")
    if sys_api and hasattr(sys_api, "NUXIVA_DIR"):
        return sys_api.NUXIVA_DIR
    return NUXIVA_DIR


def _write_env(updates: dict) -> None:
    import sys
    sys_api = sys.modules.get("system_api")
    if sys_api and hasattr(sys_api, "write_env"):
        return sys_api.write_env(updates)
    return write_env(updates)


def _env_get(key: str, default: str = "") -> str:
    import sys
    sys_api = sys.modules.get("system_api")
    if sys_api and hasattr(sys_api, "env_get"):
        return sys_api.env_get(key, default)
    return env_get(key, default)


def get_display_settings() -> dict:
    path = _nuxiva_dir() / "display_settings.json"
    if path.is_file():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {**DEFAULT_DISPLAY_SETTINGS, **data, "surfaces": _surfaces(data.get("surfaces")),
                            "screen_roles": _screen_roles(data.get("screen_roles"))}
        except (OSError, ValueError) as exc:
            log.warning("Impostazioni del display non lette: %s", exc)
    return {**DEFAULT_DISPLAY_SETTINGS, "surfaces": _surfaces(None)}


def save_display_settings(data: dict) -> dict:
    current = get_display_settings()
    for k in DEFAULT_DISPLAY_SETTINGS:
        if k in data:
            if k == "session_mode":
                val = str(data[k]).strip().lower()
                current[k] = val if val in ("shared", "isolated") else "shared"
            elif k == "surfaces":
                current[k] = _surfaces(data[k], current.get("surfaces"))
            elif k == "screen_roles":
                current[k] = _screen_roles(data[k])
            else:
                current[k] = bool(data[k])
    path = _nuxiva_dir() / "display_settings.json"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
    except OSError as exc:
        log.error("Impostazioni del display non salvate: %s", exc)
    store.display_settings = current
    try:
        from agenti.desktop.desk import desk
        desk.publish()
    except Exception:
        pass
    return current


def get_backend_settings() -> dict:
    env = read_env()
    path = _nuxiva_dir() / "backend_settings.json"
    local_data = {}
    if path.is_file():
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    local_data = loaded
        except (OSError, ValueError) as exc:
            log.warning("Impostazioni del backend non lette: %s", exc)
    return {
        **DEFAULT_BACKEND_SETTINGS,
        **local_data,
        "ollama_url": env.get("NUXIVA_OLLAMA_URL", local_data.get("ollama_url", DEFAULT_BACKEND_SETTINGS["ollama_url"])),
        "active_llm_model": env.get("NUXIVA_LLM_MODEL", local_data.get("active_llm_model", DEFAULT_BACKEND_SETTINGS["active_llm_model"])),
        "fast_llm_model": env.get("NUXIVA_LLM_FAST_MODEL", local_data.get("fast_llm_model", DEFAULT_BACKEND_SETTINGS["fast_llm_model"])),
    }


MODEL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}$")
LAN_SUFFIXES = (".local", ".lan", ".home", ".home.arpa", ".internal")


def _lan_host(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        name = host.lower().rstrip(".")
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?)*", name):
            return False
        return name == "localhost" or "." not in name or name.endswith(LAN_SUFFIXES)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return (ip.is_loopback or ip.is_private or ip.is_link_local) and not (ip.is_multicast or ip.is_unspecified or ip.is_reserved)


def safe_ollama_url(value: str) -> str:
    url = normalize_ollama(value)
    if not url:
        return ""
    if len(url) > 200 or any(ord(c) < 33 or ord(c) > 126 for c in url):
        raise HTTPException(400, "Indirizzo del server Ollama non valido")
    parts = urlsplit(url)
    try:
        port = parts.port
    except ValueError:
        raise HTTPException(400, "Porta del server Ollama non valida")
    if (parts.scheme not in ("http", "https") or parts.username is not None or parts.password is not None
            or parts.query or parts.fragment or parts.path not in ("", "/") or not parts.hostname or not port):
        raise HTTPException(400, "Indirizzo del server Ollama non valido")
    if not _lan_host(parts.hostname) and _env_get("NUXIVA_ALLOW_REMOTE_OLLAMA", "off") != "on":
        raise HTTPException(400, "Il server Ollama deve essere su questo computer o sulla rete di casa")
    return url


def safe_model(value: str) -> str:
    model = value.strip()
    if model and not MODEL_NAME.match(model):
        raise HTTPException(400, "Nome del modello non valido")
    return model


def save_backend_settings(data: dict) -> dict:
    current = get_backend_settings()
    env_updates = {}
    if "ollama_url" in data and isinstance(data["ollama_url"], str):
        url = safe_ollama_url(data["ollama_url"])
        current["ollama_url"] = url
        env_updates["NUXIVA_OLLAMA_URL"] = url
    if "active_llm_model" in data and isinstance(data["active_llm_model"], str):
        model = safe_model(data["active_llm_model"])
        current["active_llm_model"] = model
        env_updates["NUXIVA_LLM_MODEL"] = model
        env_updates["NUXIVA_LLM_CHAT_ORDER"] = model
    if "fast_llm_model" in data and isinstance(data["fast_llm_model"], str):
        fmodel = safe_model(data["fast_llm_model"])
        current["fast_llm_model"] = fmodel
        env_updates["NUXIVA_LLM_FAST_MODEL"] = fmodel
    for bool_key in ("auto_shutdown_local_ollama", "mesh_broadcast", "mesh_state_sync", "process_watchdog", "verbose_telemetry"):
        if bool_key in data:
            current[bool_key] = bool(data[bool_key])
    path = _nuxiva_dir() / "backend_settings.json"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
    except OSError as exc:
        log.error("Impostazioni del backend non salvate: %s", exc)
    if env_updates:
        _write_env(env_updates)
        _ollama_cache.clear()
        brains.invalidate()
    return current


async def _json_object(request: Request) -> dict:
    raw = await request.body()
    if len(raw) > 64 * 1024:
        raise HTTPException(413, "Richiesta troppo grande")
    try:
        body = json.loads(raw or b"{}")
    except ValueError:
        raise HTTPException(400, "JSON non valido")
    if not isinstance(body, dict):
        raise HTTPException(400, "Corpo richiesta non valido")
    return body


@public_routes.get("/api/system/display-settings")
@admin_routes.get("/api/system/display-settings")
async def get_system_display_settings():
    return {"ok": True, "settings": get_display_settings()}


@admin_routes.post("/api/system/display-settings")
async def post_system_display_settings(request: Request, _: str = Depends(require_admin)):
    return {"ok": True, "settings": save_display_settings(await _json_object(request))}


@public_routes.post("/api/system/display-settings")
async def post_display_settings_from_display(request: Request):
    require_display(request, "Solo dal display")
    return {"ok": True, "settings": save_display_settings(await _json_object(request))}


@public_routes.get("/api/system/backend-settings")
async def get_backend_settings_from_display(request: Request):
    require_display(request, "Solo dal display")
    return JSONResponse({"ok": True, "settings": get_backend_settings()}, headers=NO_CACHE)


@admin_routes.get("/api/system/backend-settings")
async def get_system_backend_settings(_: str = Depends(require_admin)):
    return JSONResponse({"ok": True, "settings": get_backend_settings()}, headers=NO_CACHE)


@admin_routes.post("/api/system/backend-settings")
async def post_system_backend_settings(request: Request, _: str = Depends(require_admin)):
    return {"ok": True, "settings": save_backend_settings(await _json_object(request))}
