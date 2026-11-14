import hashlib
import time

from access import require_admin
from config import EDITABLE_KEYS, NUXIVA_DIR, NODE, node_keys, read_global_env
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from fastapi.responses import FileResponse
from state import store
from config import PUBLIC_PORT

from agenti.nodes import compute_routes, deviceauth, enroll_routes, esp32_routes, server, trust_routes
from agenti.nodes.audit import audit
from agenti.nodes.beacon import beacon
from agenti.nodes.requests import requests
from agenti.nodes.inbox import inbox
from agenti.nodes.registry import COMMANDS, TYPES, registry

INBOX_WAIT = 25.0

public_routes = APIRouter(dependencies=[Depends(deviceauth.guard)])
admin_routes = APIRouter()
_failures: dict[str, list[float]] = {}
public_routes.include_router(enroll_routes.public_routes)
public_routes.include_router(compute_routes.public_routes)
public_routes.include_router(esp32_routes.public_routes)
admin_routes.include_router(compute_routes.admin_routes)
admin_routes.include_router(enroll_routes.admin_routes)
admin_routes.include_router(esp32_routes.admin_routes)
admin_routes.include_router(trust_routes.admin_routes)


def _ip(request: Request) -> str:
    return request.client.host if request.client else "?"


def _limited(ip: str) -> bool:
    recent = [t for t in _failures.get(ip, []) if time.time() - t < 300]
    _failures[ip] = recent
    return len(recent) >= 5


async def _body(request: Request, limit: int = 16384) -> dict:
    if int(request.headers.get("content-length") or 0) > limit:
        raise HTTPException(413, "Richiesta troppo grande")
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "Richiesta non valida")
    return body


@public_routes.post("/api/nodes/pair")
async def node_pair(request: Request):
    ip = _ip(request)
    if _limited(ip):
        raise HTTPException(429, "Troppi tentativi: riprova tra qualche minuto")
    body = await _body(request)
    try:
        token = registry.pair(str(body.get("code", "")), body.get("id"), body)
    except PermissionError as exc:
        _failures.setdefault(ip, []).append(time.time())
        store.event("WARN", f"Abbinamento nodo rifiutato da {ip}", "nodes")
        raise HTTPException(403, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    store.event("INFO", f"Nuovo nodo abbinato: {body.get('name') or body.get('id')} ({ip})", "nodes")
    return {"token": token, "heartbeat": 30}


@public_routes.post("/api/nodes/heartbeat")
async def node_heartbeat(request: Request):
    body = await _body(request)
    auth = request.headers.get("authorization", "")
    try:
        node = registry.authenticate(request.headers.get("x-nuxiva-node", ""), auth.removeprefix("Bearer ").strip())
    except PermissionError as exc:
        raise HTTPException(401, str(exc))
    was_online = time.time() - node.get("last_seen", 0) < 90
    commands = registry.heartbeat(node, body, _ip(request))
    if not was_online:
        store.event("INFO", f"Nodo online: {node['name']}", "nodes")
    return {"commands": commands, "actions": inbox.take(node["id"]), "heartbeat": 30, "agent": _agent_sha(),
            "assistant_name": _assistant_name(),
            "settings": registry.effective(node["id"]), "custom": sorted(node.get("settings") or {})}


@public_routes.post("/api/nodes/inbox")
async def node_inbox(request: Request):
    auth = request.headers.get("authorization", "")
    try:
        node = registry.authenticate(request.headers.get("x-nuxiva-node", ""), auth.removeprefix("Bearer ").strip())
    except PermissionError as exc:
        raise HTTPException(401, str(exc))
    return {"actions": await inbox.wait(node["id"], INBOX_WAIT)}


def _assistant_name() -> str:
    from identity import assistant_name

    return assistant_name()


def _agent_path():
    return NUXIVA_DIR / "client_satellite" / "linux_edge" / "satellite.py"


def _agent_sha() -> str:
    try:
        return hashlib.sha256(_agent_path().read_bytes()).hexdigest()
    except OSError:
        return ""


@public_routes.post("/api/nodes/request")
async def node_request(request: Request):
    ip = _ip(request)
    if _limited(ip):
        raise HTTPException(429, "Troppi tentativi: riprova tra qualche minuto")
    body = await _body(request)
    try:
        result = requests.submit(body, ip)
    except PermissionError as exc:
        _failures.setdefault(ip, []).append(time.time())
        raise HTTPException(409, str(exc))
    except ValueError as exc:
        _failures.setdefault(ip, []).append(time.time())
        raise HTTPException(400, str(exc))
    store.event("INFO", f"Il nodo {body.get('name') or body.get('id')} ({ip}) chiede di unirsi: codice {result['fingerprint']}",
                "nodes")
    return result


@public_routes.post("/api/nodes/claim")
async def node_claim(request: Request):
    ip = _ip(request)
    if _limited(ip):
        raise HTTPException(429, "Troppi tentativi: riprova tra qualche minuto")
    body = await _body(request)
    claim_id = str(body.get("id") or "")
    proven = False
    if requests.is_signed(claim_id):
        try:
            if not getattr(request.state, "device_verified", False):
                await deviceauth.verify(request, claim_id, requests.pubkey_of(claim_id))
        except HTTPException:
            _failures.setdefault(ip, []).append(time.time())
            raise
        proven = True
    try:
        token = requests.claim(claim_id, str(body.get("key") or ""), proven)
        if token:
            audit.record("node", claim_id, "pair.claim", ip)
    except PermissionError as exc:
        _failures.setdefault(ip, []).append(time.time())
        raise HTTPException(403, str(exc))
    return {"approved": bool(token), "token": token, "heartbeat": 30} if token else {"approved": False}


@admin_routes.get("/api/nodes")
async def nodes_overview(_: str = Depends(require_admin)):
    paired = {n["id"] for n in registry.listing()}
    return {"master": server.master(), "nodes": registry.listing(), "types": TYPES, "commands": COMMANDS,
            "pending": requests.listing(), "found": [f for f in beacon.found() if f["id"] not in paired]}


class ApproveBody(BaseModel):
    profile: str = Field("satellite", max_length=16)
    allow_second_server: bool = False
    grants: list[str] = Field(default_factory=list, max_length=8)


@admin_routes.post("/api/nodes/requests/{node_id}/approve")
async def nodes_approve(node_id: str, body: ApproveBody | None = None, user: str = Depends(require_admin)):
    body = body or ApproveBody()
    try:
        req = requests.approve(node_id, body.profile, body.allow_second_server, body.grants)
    except KeyError:
        raise HTTPException(404, "Richiesta scaduta o inesistente")
    except (PermissionError, ValueError) as exc:
        raise HTTPException(400, str(exc))
    store.event("INFO", f"Nodo {req['name']} approvato da {user}", "nodes")
    audit.record(user, node_id, "pair.approve", f"{body.profile} second_server={body.allow_second_server} grants={','.join(body.grants)}")
    return {"ok": True}


@admin_routes.delete("/api/nodes/requests/{node_id}")
async def nodes_reject(node_id: str, user: str = Depends(require_admin)):
    requests.reject(node_id)
    audit.record(user, node_id, "pair.reject")
    store.event("INFO", f"Richiesta del nodo {node_id} rifiutata da {user}", "nodes")
    return {"ok": True}


@admin_routes.post("/api/nodes/pairing-code")
async def nodes_code(user: str = Depends(require_admin)):
    store.event("INFO", f"Codice di abbinamento nodi generato da {user}", "nodes")
    from agenti.nodes import trust
    return {**registry.new_code(), "ca_fingerprint": trust.ca_fingerprint()}


@admin_routes.get("/api/nodes/connection")
async def nodes_connection(request: Request, _: str = Depends(require_admin)):
    url = request.url.replace(path="", query="")
    if not request.scope.get("root_path", "").endswith("/admin"):
        url = url.replace(scheme="http", port=PUBLIC_PORT)
    return {"server": str(url).rstrip("/")}


@admin_routes.put("/api/nodes/{node_id}")
async def nodes_update(node_id: str, request: Request, _: str = Depends(require_admin)):
    try:
        registry.update(node_id, await _body(request))
    except KeyError as exc:
        raise HTTPException(404, f"Nodo non trovato: {exc}")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"nodes": registry.listing()}


@admin_routes.get("/api/nodes/{node_id}/settings")
async def nodes_settings(node_id: str, _: str = Depends(require_admin)):
    try:
        node = registry.data["nodes"][node_id]
    except KeyError:
        raise HTTPException(404, "Nodo non trovato")
    env, custom = read_global_env(), node.get("settings") or {}
    return {"node": {k: v for k, v in node.items() if k != "token"},
            "items": [{"key": k, "label": EDITABLE_KEYS[k], "global": env.get(k, ""), "value": custom.get(k, ""),
                       "custom": k in custom} for k in node_keys()]}


@public_routes.post("/api/nodes/chat")
async def node_chat(request: Request):
    body = await _body(request)
    auth = request.headers.get("authorization", "")
    try:
        node = registry.authenticate(request.headers.get("x-nuxiva-node", ""), auth.removeprefix("Bearer ").strip())
    except PermissionError as exc:
        raise HTTPException(401, str(exc))
    from agenti.chat.api import assistant_chat
    NODE.set(node["id"])
    return await assistant_chat(str(body.get("text", "")), node["id"], str(body.get("lang") or "") or None)


def _node(request: Request) -> dict:
    auth = request.headers.get("authorization", "")
    try:
        return registry.authenticate(request.headers.get("x-nuxiva-node", ""), auth.removeprefix("Bearer ").strip())
    except PermissionError as exc:
        raise HTTPException(401, str(exc))


@public_routes.post("/api/nodes/assist")
async def node_assist(request: Request):
    node = _node(request)
    body = await _body(request, 12 * 1024 * 1024)
    from agenti.nodes import assist_turn
    from agenti.nodes import desk_assistant
    NODE.set(node["id"])
    return await assist_turn.run(node["id"], body.get("turn_id"), lambda: desk_assistant.assist(node, body))


@public_routes.post("/api/nodes/memory-sync")
async def node_memory_sync(request: Request):
    node = _node(request)
    body = await _body(request, 256 * 1024)
    turns = body.get("turns")
    if not isinstance(turns, list) or len(turns) > 50:
        raise HTTPException(400, "Richiesta non valida")
    from agenti.chat import dialogue as dialogue_mod

    stored = 0
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        text, reply = turn.get("text"), turn.get("reply")
        if isinstance(text, str) and isinstance(reply, str) and text.strip():
            dialogue_mod.dialogue.remember(node["id"], text[:600], reply[:600], "pc")
            stored += 1
    return {"stored": stored}


@public_routes.post("/api/nodes/assist/stop")
async def node_assist_stop(request: Request):
    node = _node(request)
    body = await _body(request, 1024)
    from agenti.nodes import assist_turn
    stopped = await assist_turn.stop(node["id"], body.get("turn_id"))
    return {"accepted": True, "stopped": stopped}


@public_routes.post("/api/nodes/tts")
async def node_tts(request: Request):
    _node(request)
    body = await _body(request, 65536)
    from agenti.voices.api import tts_response
    return await tts_response(str(body.get("text", ""))[:3000], str(body.get("lang") or "")[:8] or None)


@public_routes.post("/api/nodes/intent")
async def node_intent(request: Request):
    body = await _body(request)
    auth = request.headers.get("authorization", "")
    try:
        node = registry.authenticate(request.headers.get("x-nuxiva-node", ""), auth.removeprefix("Bearer ").strip())
    except PermissionError as exc:
        raise HTTPException(401, str(exc))
    from agenti.chat.api import assistant_chat
    from agenti.nodes.edge import edge_claim, fast_path
    NODE.set(node["id"])
    text = " ".join(str(body.get("text", "")).split())
    result = await fast_path(text, edge_claim(body))
    if result is not None:
        return result
    return await assistant_chat(text, node["id"], str(body.get("lang") or "") or None)


@admin_routes.post("/api/nodes/master/adapt")
async def nodes_master_adapt(user: str = Depends(require_admin)):
    from agenti.nodes import adapt
    report = await adapt.run_master()
    store.event("INFO", f"Auto-adattamento del server richiesto da {user}", "nodes")
    return report


@admin_routes.get("/api/nodes/master/adaptation")
async def nodes_master_adaptation(_: str = Depends(require_admin)):
    from agenti.nodes import adapt
    return adapt.read_snapshot()


@admin_routes.post("/api/nodes/{node_id}/command/{command}")
async def nodes_command(node_id: str, command: str, user: str = Depends(require_admin)):
    try:
        registry.command(node_id, command)
    except KeyError:
        raise HTTPException(404, "Nodo non trovato")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    store.event("INFO", f"Comando «{COMMANDS[command]}» al nodo {node_id} da {user}", "nodes")
    return {"ok": True}


@admin_routes.delete("/api/nodes/{node_id}")
async def nodes_remove(node_id: str, user: str = Depends(require_admin)):
    try:
        registry.remove(node_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    audit.record(user, node_id, "node.revoke")
    store.event("INFO", f"Nodo {node_id} rimosso da {user}: il suo token non vale più", "nodes")
    return {"nodes": registry.listing()}


@public_routes.get("/nodes/agent.py")
async def node_agent():
    path = _agent_path()
    if not path.is_file():
        raise HTTPException(404, "Agente non disponibile")
    return FileResponse(path, media_type="text/x-python", filename="nuxiva-node.py")
