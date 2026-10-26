import asyncio
import json
import socket
import threading
import time
from urllib.parse import urlparse

from fastapi import Request
from fastapi.responses import StreamingResponse

from access import NO_CACHE
from config import ADMIN_PORT, NODE, OLLAMA_URL, PUBLIC_PORT, STATE_DIR, VERSION, read_env
from features.brain.brains import brains
from features.home_assistant import home
from features.music import music
from orchestrator import orch
from pages import ASSET_VERSION, face_options
from state import store
from steps import step_catalog


FACE_KEYS = {"NUXIVA_AVATAR", "NUXIVA_FACE_COLOR"}


def _node_faces() -> dict:
    faces = {}
    for nid in node_ids_with(FACE_KEYS):
        token = NODE.set(nid)
        try:
            faces[nid] = face_options()
        finally:
            NODE.reset(token)
    return faces


def node_ids_with(keys: set) -> list[str]:
    path = STATE_DIR / "nodes.json"
    try:
        nodes = json.loads(path.read_text(encoding="utf-8")).get("nodes", {})
    except (OSError, ValueError):
        return []
    return [nid for nid, n in nodes.items() if keys & set(n.get("settings") or {})]


def _satellites() -> list[dict]:
    try:
        from features.nodes.registry import registry
        return registry.listing()
    except Exception:
        return []


SERVER_PROBE_TTL = 15.0
_servers_cache: dict = {"at": 0.0, "items": [], "running": False}
_servers_lock = threading.Lock()


def _server_targets() -> list[dict]:
    ollama = urlparse(read_env().get("NUXIVA_OLLAMA_URL") or OLLAMA_URL)
    return [
        {"id": "supervisor", "name": "Supervisore", "role": "Amministrazione", "host": "127.0.0.1", "port": ADMIN_PORT, "protocol": "HTTP/SSE"},
        {"id": "public", "name": "Display kiosk", "role": "Pagina pubblica e schermi", "host": "127.0.0.1", "port": PUBLIC_PORT, "protocol": "HTTP"},
        {"id": "core", "name": "Nuxiva Core", "role": "Assistente e API", "host": "127.0.0.1", "port": 8443, "protocol": "HTTP/WebSocket"},
        {"id": "ollama", "name": "Motore neurale", "role": "Ollama", "host": ollama.hostname or "127.0.0.1", "port": ollama.port or 11434, "protocol": "HTTP"},
        {"id": "qdrant", "name": "Memoria vettoriale", "role": "Qdrant", "host": "127.0.0.1", "port": 6333, "protocol": "HTTP"},
        {"id": "homeassistant", "name": "Home Assistant", "role": "Domotica", "host": "127.0.0.1", "port": 8123, "protocol": "HTTP/WebSocket"},
    ]


def _probe(target: dict) -> dict:
    start = time.perf_counter()
    try:
        with socket.create_connection((target["host"], target["port"]), timeout=0.4):
            latency = round((time.perf_counter() - start) * 1000, 1)
        status = "online"
    except OSError:
        latency, status = None, "offline"
    return {**{k: v for k, v in target.items() if k != "host"}, "status": status, "latency_ms": latency}


def _refresh_servers() -> None:
    try:
        items = [_probe(t) for t in _server_targets()]
    except Exception:
        items = []
    with _servers_lock:
        _servers_cache.update(at=time.time(), items=items, running=False)


def _connected_servers() -> list[dict]:
    with _servers_lock:
        stale = time.time() - _servers_cache["at"] > SERVER_PROBE_TTL
        if stale and not _servers_cache["running"]:
            _servers_cache["running"] = True
            threading.Thread(target=_refresh_servers, name="server-probe", daemon=True).start()
        return list(_servers_cache["items"])


def full_snapshot(admin: bool) -> dict:
    snap = store.snapshot(admin=admin, log_lines=40 if admin else 14)
    snap["catalog"] = step_catalog()
    snap["supervisor_version"] = VERSION
    snap["asset_version"] = ASSET_VERSION
    env = read_env()
    snap["llm_model"] = env.get("NUXIVA_LLM_MODEL", "")
    cfg = brains.config()
    chat, deep = brains.active_now("chat"), brains.active_now("deep")
    last = brains.last.get("model", "")
    snap["brains"] = {"chat": chat["label"] if chat else cfg["chat"][0], "deep": deep["label"] if deep else cfg["deep"][0],
                      "routing": cfg["routing"], "last": brains.describe(last)["label"] if last else ""}
    snap["user_name"] = env.get("NUXIVA_USER_NAME", "")
    snap["face"] = face_options()
    snap["node_faces"] = _node_faces()
    snap["mic_reset"] = getattr(store, "mic_reset", 0)
    snap["now_playing"] = music.watcher.current()
    snap["home"] = home.brain.brief()
    snap["selftest"] = getattr(store, "selftest", None)
    from background import queue
    snap["background"] = queue.snapshot()
    try:
        from features.sounds.policy import policy as sound_policy
        snap["sounds"] = sound_policy.state()
    except Exception:
        snap["sounds"] = None
    if admin:
        snap["model_pull"] = getattr(store, "model_pull", None)
        snap["voice_pull"] = getattr(store, "voice_pull", None)
        snap["busy"] = orch.busy
        snap["satellites"] = _satellites()
        snap["connected_servers"] = _connected_servers()
    try:
        from system_api import get_display_settings
        snap["display_settings"] = get_display_settings()
    except Exception:
        pass
    if hasattr(store, "holo_action"):
        snap["holo_action"] = store.holo_action
        delattr(store, "holo_action")
    return snap


def sse(admin: bool):
    async def generator(request: Request):
        last_version, last_sent = -1, 0.0
        while not await request.is_disconnected():
            if store.version != last_version or time.time() - last_sent > 10:
                last_version, last_sent = store.version, time.time()
                yield f"data: {json.dumps(full_snapshot(admin), ensure_ascii=False, default=str)}\n\n"
            await asyncio.sleep(0.5)

    async def endpoint(request: Request):
        return StreamingResponse(generator(request), media_type="text/event-stream",
                                 headers={**NO_CACHE, "X-Accel-Buffering": "no"})
    return endpoint
