import shutil
import subprocess
from dataclasses import asdict
from typing import Any, Dict

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from access import require_admin
from config import ollama_url
from .bench import run_benchmark
from .hardware import calculate_hardware_profile
from .service import (
    apply_systemd_configuration,
    get_default_config,
    load_config,
    save_config,
)
from .types import OllamaRuntimeConfig

admin_routes = APIRouter()
public_routes = APIRouter()


async def _probe_daemon(url: str) -> tuple[bool, str, list[str]]:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{url}/api/version")
            if resp.status_code == 200:
                ver = resp.json().get("version", "unknown")
                tags_resp = await client.get(f"{url}/api/tags")
                models = []
                if tags_resp.status_code == 200:
                    models = [m.get("name", "") for m in tags_resp.json().get("models", [])]
                return True, ver, models
    except (httpx.HTTPError, OSError):
        pass
    return False, "offline", []


@admin_routes.get("/api/ollama/status")
async def get_ollama_status(request: Request, _auth: None = Depends(require_admin)) -> Dict[str, Any]:
    url = ollama_url()
    online, version, active_models = await _probe_daemon(url)
    config = load_config()
    profile = calculate_hardware_profile()
    return {
        "online": online,
        "version": version,
        "active_models": active_models,
        "host": url,
        "config": config.to_dict(),
        "hardware": asdict(profile),
    }


@admin_routes.get("/api/ollama/hardware")
async def get_hardware_analysis(request: Request, _auth: None = Depends(require_admin)) -> Dict[str, Any]:
    profile = calculate_hardware_profile()
    return asdict(profile)


@admin_routes.put("/api/ollama/config")
async def update_ollama_config(payload: Dict[str, Any], request: Request, _auth: None = Depends(require_admin)) -> Dict[str, Any]:
    current = load_config()
    updated_dict = current.to_dict()

    for key, value in payload.items():
        if key in updated_dict:
            if key in ("num_parallel", "num_ctx", "num_predict", "max_loaded_models", "cpu_weight", "nice", "num_thread", "max_queue"):
                try:
                    updated_dict[key] = int(value)
                except (ValueError, TypeError):
                    raise HTTPException(status_code=400, detail=f"Valore intero non valido per {key}")
            elif key == "flash_attention":
                updated_dict[key] = bool(value)
            elif key in ("keep_alive", "mode"):
                updated_dict[key] = str(value).strip()

    updated_config = OllamaRuntimeConfig.from_dict(updated_dict)
    save_config(updated_config)
    applied = apply_systemd_configuration(updated_config)
    return {
        "status": "success",
        "applied_systemd": applied,
        "config": updated_config.to_dict(),
    }


@admin_routes.post("/api/ollama/reset-auto")
async def reset_to_hardware_defaults(request: Request, _auth: None = Depends(require_admin)) -> Dict[str, Any]:
    default_cfg = get_default_config()
    save_config(default_cfg)
    applied = apply_systemd_configuration(default_cfg)
    profile = calculate_hardware_profile()
    return {
        "status": "success",
        "applied_systemd": applied,
        "config": default_cfg.to_dict(),
        "hardware": asdict(profile),
    }


@admin_routes.post("/api/ollama/restart")
async def restart_ollama_service(request: Request, _auth: None = Depends(require_admin)) -> Dict[str, Any]:
    if not shutil.which("systemctl"):
        return {"status": "skipped", "message": "systemctl non disponibile"}
    try:
        subprocess.run(["systemctl", "restart", "ollama"], check=True, timeout=15)
        return {"status": "success"}
    except (OSError, subprocess.SubprocessError) as exc:
        raise HTTPException(status_code=500, detail=f"Errore nel riavvio del servizio: {exc}")


@admin_routes.post("/api/ollama/bench")
async def execute_benchmark(payload: Dict[str, Any], request: Request, _auth: None = Depends(require_admin)) -> Dict[str, Any]:
    url = ollama_url()
    model = payload.get("model", "")
    try:
        res = await run_benchmark(url, model=model)
        return asdict(res)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Benchmark fallito: {exc}")
