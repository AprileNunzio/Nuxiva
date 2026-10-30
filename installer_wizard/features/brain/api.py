import hashlib
import json
import os
import logging
import re

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

import health
from access import require_admin
from config import ollama_url, read_env, write_env
from feature_registry import registry
from features.brain import assignments_api, bridge, cervello_state, chains_api
from features.brain.free_router.api import admin_routes as free_matrix_routes
from features.brain.decision_lab.api import admin_routes as decision_lab_routes, public_routes as decision_lab_public_routes
from features.brain.usage import api as usage_api
from features.brain.brains import brains
from features.brain.configuration import bound_selection
from features.brain.residency import rebalance
from features.brain.roles import ROLES
import licensing
from state import store
from tasks import background

admin_routes = APIRouter()
admin_routes.include_router(assignments_api.admin_routes)
admin_routes.include_router(bridge.admin_routes)
admin_routes.include_router(chains_api.admin_routes)
admin_routes.include_router(free_matrix_routes)
admin_routes.include_router(decision_lab_routes)
admin_routes.include_router(usage_api.admin_routes)
public_routes = assignments_api.public_routes
public_routes.include_router(decision_lab_public_routes)
public_routes.include_router(usage_api.public_routes)
log = logging.getLogger("nuxiva.brain")
_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,119}$")


async def pull_model(name: str) -> None:
    store.model_pull = {"name": name, "status": "avvio", "percent": 0}
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", f"{ollama_url()}/api/pull", json={"model": name}) as resp:
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    msg = json.loads(line)
                    if "error" in msg:
                        raise RuntimeError(msg["error"])
                    pct = int(msg["completed"] * 100 / msg["total"]) if msg.get("total") and msg.get("completed") else None
                    store.model_pull = {"name": name, "status": msg.get("status", ""),
                                        "percent": pct if pct is not None else store.model_pull["percent"]}
                    store.touch()
        store.model_pull = {"name": name, "status": "completato", "percent": 100}
        store.event("INFO", f"Modello scaricato: {name}", "models")
        brains.invalidate()
    except Exception as exc:
        store.model_pull = {"name": name, "status": f"errore: {exc}", "percent": 0}
        store.event("ERROR", f"Download modello {name} non riuscito: {exc}", "models")
    store.touch()


@admin_routes.post("/api/models/probe")
@admin_routes.post("/api/brain/ollama/probe")
@admin_routes.post("/api/v2/brain/ollama/probe")
async def probe_ollama_remote(request: Request):
    body = await request.json()
    host = str(body.get("host") or "").strip() if isinstance(body, dict) else ""
    if not host:
        return {"online": False, "models": [], "error": "missing_host"}

    if not host.startswith("http://") and not host.startswith("https://"):
        host = f"http://{host}"
    parts = host.split("/")
    if ":" not in parts[-1] and (len(parts) <= 3 or ":" not in parts[2]):
        host = f"{host.rstrip('/')}:11434"
    normalized = host.rstrip("/")

    import time
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            tags_res = None
            try:
                tags_res = await client.get(f"{normalized}/api/tags")
            except Exception:
                tags_res = None

            latency_ms = int((time.perf_counter() - start) * 1000)

            if tags_res is not None and tags_res.status_code == 200:
                data = tags_res.json()
                raw_models = data.get("models", [])
                parsed = [
                    {
                        "name": str(m.get("name") or m.get("model") or ""),
                        "size": int(m.get("size") or 0),
                        "parameter_size": str(m.get("details", {}).get("parameter_size") or ""),
                        "quantization_level": str(m.get("details", {}).get("quantization_level") or ""),
                        "family": str(m.get("details", {}).get("family") or ""),
                        "modified_at": str(m.get("modified_at") or ""),
                    }
                    for m in raw_models
                ]
                return {
                    "online": True,
                    "latency_ms": latency_ms,
                    "normalized_url": normalized,
                    "models": parsed,
                }

            try:
                root_res = await client.get(f"{normalized}/")
                if root_res.status_code == 200 and (
                    "ollama" in root_res.text.lower() or "running" in root_res.text.lower()
                ):
                    return {
                        "online": True,
                        "latency_ms": latency_ms,
                        "normalized_url": normalized,
                        "models": [],
                    }
            except Exception:
                pass

            try:
                ver_res = await client.get(f"{normalized}/api/version")
                if ver_res.status_code == 200:
                    return {
                        "online": True,
                        "latency_ms": latency_ms,
                        "normalized_url": normalized,
                        "models": [],
                    }
            except Exception:
                pass

            return {
                "online": False,
                "latency_ms": latency_ms,
                "normalized_url": normalized,
                "error": "host_unreachable_or_not_ollama",
            }
    except Exception as exc:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            "online": False,
            "latency_ms": latency_ms,
            "normalized_url": normalized,
            "error": str(exc),
        }


async def unload_local_ollama_vram() -> dict:
    local_url = "http://127.0.0.1:11434"
    unloaded = []
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            try:
                ps = await client.get(f"{local_url}/api/ps")
                if ps.status_code == 200:
                    for mod in ps.json().get("models", []):
                        m_name = mod.get("name") or mod.get("model")
                        if m_name:
                            try:
                                await client.post(f"{local_url}/api/generate", json={"model": m_name, "keep_alive": 0})
                                unloaded.append(m_name)
                            except Exception:
                                pass
            except Exception:
                pass
    except Exception as exc:
        log.warning("Unload local Ollama VRAM failed: %s", exc)
    return {"unloaded": unloaded}


@admin_routes.post("/api/v2/brain/assignments/batch")
@public_routes.post("/api/v2/brain/assignments/batch")
async def batch_save_brain_assignments(request: Request):
    body = await request.json()
    model_name = str(body.get("modelName", "")).strip()
    base_url = str(body.get("baseUrl", "")).strip()
    provider = str(body.get("provider", "ollama_local")).strip()
    if provider not in ("ollama_local", "ollama_remote", "api_key", "cloud") or not model_name:
        raise HTTPException(400, "Provider o modello non valido")
    if provider == "ollama_remote" and not base_url:
        raise HTTPException(400, "Indirizzo Ollama remoto mancante")
    if provider in ("api_key", "cloud"):
        from features.cloud.catalog import make_ref, parse_ref, is_cloud
        pid = str(body.get("serverId") or body.get("providerId") or "")
        pid = {"google": "gemini"}.get(pid, pid)
        model_name = model_name if is_cloud(model_name) else make_ref(pid, model_name)
        try:
            parse_ref(model_name)
        except ValueError as exc:
            raise HTTPException(400, str(exc))

    updates = {"NUXIVA_BRAIN": "cloud" if provider in ("api_key", "cloud") else "local"}
    if base_url and provider == "ollama_remote":
        base_url = base_url.rstrip("/")
        if not base_url.startswith(("http://", "https://")):
            base_url = f"http://{base_url}"
        if not re.search(r":\d+$", base_url.split("//", 1)[1]):
            base_url = f"{base_url}:11434"
        updates["NUXIVA_OLLAMA_URL"] = base_url
    elif provider == "ollama_local":
        updates["NUXIVA_OLLAMA_URL"] = "http://127.0.0.1:11434"

    if model_name:
        updates["NUXIVA_LLM_MODEL"] = model_name
        updates["NUXIVA_LLM_FAST_MODEL"] = model_name
        updates["NUXIVA_LLM_CHAT_ORDER"] = model_name
        updates["NUXIVA_LLM_DEEP_ORDER"] = model_name
        for role in ROLES:
            updates[role.env_key] = model_name
            updates[role.scope_key] = ""
            updates[role.strategy_key] = ""

    if updates:
        write_env(updates)
        for k, v in updates.items():
            os.environ[k] = str(v)
        try:
            from config import _ollama_cache

            _ollama_cache.clear()
        except Exception:
            pass
        from features.brain.routing import assignment_service
        from features.brain.free_router import settings as free_settings
        free_config = free_settings.load()
        if free_config["enabled"]:
            free_settings.save(False, free_config["pools"])
        assignment_service.save({key: None for key in assignment_service.assignments() if not key.startswith("agent:")})
        cervello_state.save({
            "globalDefault": {
                **(body.get("globalDefault") or {}),
                "provider": provider, "serverId": body.get("serverId"),
                "baseUrl": base_url, "modelName": model_name,
            },
            "targets": body.get("targets", []),
        })
        brains.invalidate()
        store.touch()

    if provider in ("ollama_remote", "cloud", "api_key"):
        await unload_local_ollama_vram()

    return {
        "status": "ok",
        "applied_model": model_name,
        "applied_url": updates.get("NUXIVA_OLLAMA_URL", ollama_url()),
        "updates": updates,
    }


@admin_routes.post("/api/v2/brain/assignments")
@public_routes.post("/api/v2/brain/assignments")
async def single_save_brain_assignment(request: Request):
    body = await request.json()
    target_id = str(body.get("targetId", "")).strip()
    try:
        assigned_model, base_url = bound_selection(body)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    updates = {}

    if assigned_model:
        if target_id in ("conversation", "jarvis_page80", "core_brain"):
            updates["NUXIVA_LLM_MODEL"] = assigned_model
            updates["NUXIVA_LLM_CHAT_ORDER"] = assigned_model
        role_id = {"fast_conversation": "chat", "reasoning": "deep"}.get(target_id, target_id)
        for role in ROLES:
            if role.id == role_id:
                updates[role.env_key] = assigned_model

    if updates:
        write_env(updates)
        for k, v in updates.items():
            os.environ[k] = str(v)
        try:
            from config import _ollama_cache

            _ollama_cache.clear()
        except Exception:
            pass
        brains.invalidate()

    return {
        "status": "ok",
        "targetId": target_id,
        "assignedModel": assigned_model,
        "applied_url": base_url or ollama_url(),
    }


@admin_routes.get("/api/v2/brain/state")
@public_routes.get("/api/v2/brain/state")
async def get_cervello_state():
    return cervello_state.load()


@admin_routes.put("/api/v2/brain/state")
@public_routes.put("/api/v2/brain/state")
async def put_cervello_state(request: Request):
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "Stato non valido")
    try:
        return cervello_state.save(body)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@admin_routes.get("/api/v2/brain/config")
@public_routes.get("/api/v2/brain/config")
async def get_v2_brain_config():
    env = read_env()
    cfg = brains.config()
    current_url = ollama_url()
    signature = json.dumps({r.id: cfg[r.id] for r in ROLES} | {"routing": cfg["routing"], "main": cfg["main"]}, sort_keys=True)
    return {
        "active": brains.active_now("chat") or brains.describe(cfg["main"]),
        "working": brains.active_now("deep") or brains.describe(cfg["main"]),
        "routing": cfg["routing"],
        "revision": hashlib.sha256(signature.encode()).hexdigest()[:16],
        "active_model": env.get("NUXIVA_LLM_MODEL") or cfg.get("main", "granite3.3:2b"),
        "ollama_url": current_url,
        "fast_model": env.get("NUXIVA_LLM_FAST_MODEL") or cfg.get("fast", ""),
        "chat_order": env.get("NUXIVA_LLM_CHAT_ORDER", ""),
        "deep_order": env.get("NUXIVA_LLM_DEEP_ORDER", ""),
    }


@admin_routes.get("/api/models")
async def list_models(_: str = Depends(require_admin)):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            tags = (await client.get(f"{ollama_url()}/api/tags")).json().get("models", [])
            loaded = [m["name"] for m in (await client.get(f"{ollama_url()}/api/ps")).json().get("models", [])]
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502, "Motore neurale non raggiungibile")
    return {"models": [{"name": m["name"], "size": m.get("size", 0), "modified": m.get("modified_at")}
                       for m in tags], "loaded": loaded}


@admin_routes.post("/api/models/pull")
async def admin_pull(request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    name = str(body.get("name", "")).strip() if isinstance(body, dict) else ""
    if not _MODEL_RE.match(name):
        raise HTTPException(400, "Nome modello non valido")
    background(pull_model(name))
    return {"ok": True, "license": licensing.describe(licensing.model_license(name))}


@admin_routes.delete("/api/models/{name:path}")
async def admin_delete_model(name: str, _: str = Depends(require_admin)):
    env, cfg = read_env(), brains.config()
    in_use = {health.norm_model(m) for m in [env.get("NUXIVA_LLM_MODEL", ""), env.get("NUXIVA_EMBED_MODEL", ""),
                                             cfg["fast"], *(m for role in ROLES for m in cfg[role.id])] if m}
    if health.norm_model(name) in in_use:
        raise HTTPException(409, "Il modello è in uso: toglilo prima dalle liste del cervello")
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.request("DELETE", f"{ollama_url()}/api/delete", json={"model": name})
    brains.invalidate()
    return {"ok": r.status_code == 200}


@admin_routes.get("/api/brains")
async def admin_brains(_: str = Depends(require_admin)):
    if not registry.hw:
        await registry.probe_hardware()
    return await brains.overview(registry.hw)


@admin_routes.put("/api/brains")
async def admin_brains_set(request: Request, user: str = Depends(require_admin)):
    body, updates = await request.json(), {}
    if "routing" in body:
        if body["routing"] not in ("auto", "1", "0"):
            raise HTTPException(400, "Modalità di instradamento non valida")
        updates["NUXIVA_LLM_ROUTING"] = body["routing"]
    for role in ROLES:
        if role.id in body:
            models = [str(m).strip() for m in (body[role.id] or []) if str(m).strip()]
            if len(models) > 12 or not all(_MODEL_RE.match(m) for m in models):
                raise HTTPException(400, "Elenco di modelli non valido")
            updates[role.env_key] = ",".join(dict.fromkeys(models))
            updates[role.profile_key] = "custom" if models else "auto"
            if not models:
                updates.update({role.scope_key: "", role.strategy_key: ""})
    if updates:
        write_env(updates)
        brains.invalidate()
        background(rebalance())
        store.event("INFO", f"Cervello aggiornato da {user}: {', '.join(updates)}", "models")
    return await brains.overview(registry.hw)


@admin_routes.post("/api/brains/test")
async def admin_brains_test(request: Request, _: str = Depends(require_admin)):
    text = str((await request.json()).get("text", ""))[:2000]
    return await brains.route(text)


@admin_routes.post("/api/brains/ollama/test")
async def admin_ollama_test(request: Request, _: str = Depends(require_admin)):
    from settings import normalize_ollama
    raw = str((await request.json()).get("url", "")).strip()
    url = normalize_ollama(raw) if raw else "http://127.0.0.1:11434"
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            version = (await client.get(f"{url}/api/version")).json().get("version", "?")
            tags = (await client.get(f"{url}/api/tags")).json().get("models", [])
    except (httpx.HTTPError, ValueError) as exc:
        return {"ok": False, "url": url, "error": f"non raggiungibile ({type(exc).__name__}): sul server remoto avvia Ollama con OLLAMA_HOST=0.0.0.0"}
    return {"ok": True, "url": url, "version": version, "models": [m.get("name", "") for m in tags]}
