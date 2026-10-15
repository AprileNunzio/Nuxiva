from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from access import require_admin
from config import NUXIVA_DIR, env_get, write_env
from fastapi import APIRouter, Depends, HTTPException
from health import sh
from pydantic import BaseModel, ConfigDict, Field
from state import store
from tasks import background

import updater
from features.update_center import diagnostics, rollout
from features.update_center.policy import PolicyError, UpdatePolicy, load_policy, next_window, policy_to_env

admin_routes = APIRouter(prefix="/api/v5/updater", tags=["Update Center"], dependencies=[Depends(require_admin)])

SUPERVISOR_UNIT = "nuxiva-supervisor"
HISTORY_LIMIT = 40
_NODE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{2,47}$")


class ConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirm: bool = False


class PolicyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    auto_update: bool
    window: str = Field(pattern=r"^$|^(?:[01]\d|2[0-3]):[0-5]\d$")
    interval_minutes: int = Field(ge=1, le=1440)
    sync_nodes: bool
    require_ci: bool


def _registry():
    from features.nodes.registry import registry

    return registry


def _version() -> Optional[str]:
    try:
        return (NUXIVA_DIR / "VERSION").read_text(encoding="utf-8").strip()[:32] or None
    except OSError:
        return None


def _policy() -> UpdatePolicy:
    return load_policy(env_get)


def _require_confirm(req: ConfirmRequest) -> None:
    if not req.confirm:
        raise HTTPException(status_code=428, detail="confirmation_required")


def _status_payload() -> Dict[str, Any]:
    info = store.update
    policy = _policy()
    upcoming = next_window(datetime.now(), policy.window) if policy.auto_update else None
    return {
        "version": _version(),
        "local_rev": info.get("local_rev") or None,
        "remote_rev": info.get("remote_rev") or None,
        "target_rev": info.get("target_rev") or None,
        "available": bool(info.get("available")),
        "changelog": list(info.get("changelog") or [])[:15],
        "last_check": info.get("last_check"),
        "last_result": info.get("last_result"),
        "ci_note": info.get("ci_note") or None,
        "phase": store.phase,
        "message": store.message,
        "pending": updater.pending(),
        "policy": policy.as_dict(),
        "next_window": upcoming.isoformat(timespec="minutes") if upcoming else None,
        "nodes": rollout.node_rollout_view(_registry().listing()),
    }


async def _apply_and_rollout(sync_nodes: bool) -> None:
    applied = await updater.apply("manuale", force=True)
    if applied and sync_nodes:
        registry = _registry()
        queued = rollout.queue_updates(registry, [n["id"] for n in registry.listing()])
        store.event("INFO", f"Aggiornamento simultaneo inviato a {len(queued)} nodi", "updater")


@admin_routes.get("/status")
async def update_status() -> Dict[str, Any]:
    return _status_payload()


@admin_routes.post("/check")
async def update_check() -> Dict[str, Any]:
    await updater.check(allow_bad=True)
    return _status_payload()


@admin_routes.post("/apply")
async def update_apply(req: ConfirmRequest, user: str = Depends(require_admin)) -> Dict[str, Any]:
    _require_confirm(req)
    info = await updater.check(allow_bad=True)
    target = info.get("target_rev") or info.get("remote_rev")
    if not target or target == info.get("local_rev"):
        raise HTTPException(status_code=409, detail="no_update_available")
    store.event("INFO", f"Aggiornamento manuale avviato da {user}", "updater")
    background(_apply_and_rollout(_policy().sync_nodes))
    return {"status": "started", "target_rev": target}


@admin_routes.put("/policy")
async def update_policy(req: PolicyRequest, user: str = Depends(require_admin)) -> Dict[str, Any]:
    policy = UpdatePolicy(**req.model_dump())
    try:
        write_env(policy_to_env(policy))
    except PolicyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    store.event("INFO", f"Politica aggiornamenti modificata da {user}", "updater")
    return _status_payload()


@admin_routes.post("/collaudo")
async def update_collaudo() -> Dict[str, Any]:
    async def memory():
        return diagnostics.check_memory()

    async def disk():
        return diagnostics.check_disk(NUXIVA_DIR)

    async def cpu():
        return diagnostics.check_cpu()

    async def worktree():
        return await diagnostics.check_worktree(updater.git)

    async def ci():
        return await diagnostics.check_ci(await updater.current_rev(), updater.ci_status)

    async def service():
        return await diagnostics.check_service(sh, SUPERVISOR_UNIT)

    async def rollback_point():
        return diagnostics.check_last_good(await updater.current_rev(), getattr(store, "last_good_rev", None))

    async def mesh_engine():
        return diagnostics.check_mesh_engine()

    steps = [memory, disk, cpu, worktree, ci, service, rollback_point, mesh_engine]
    for step in steps:
        step.check_id = step.__name__
    return await diagnostics.run_all(steps)


@admin_routes.post("/nodes/update")
async def update_all_nodes(req: ConfirmRequest, user: str = Depends(require_admin)) -> Dict[str, Any]:
    _require_confirm(req)
    registry = _registry()
    queued = rollout.queue_updates(registry, [n["id"] for n in registry.listing()])
    store.event("INFO", f"Aggiornamento di {len(queued)} nodi richiesto da {user}", "updater")
    return {"queued": queued}


@admin_routes.post("/nodes/{node_id}/update")
async def update_node(node_id: str, req: ConfirmRequest, user: str = Depends(require_admin)) -> Dict[str, Any]:
    _require_confirm(req)
    if not _NODE_ID.match(node_id):
        raise HTTPException(status_code=422, detail="invalid_node_id")
    queued = rollout.queue_updates(_registry(), [node_id])
    if not queued:
        raise HTTPException(status_code=404, detail="node_not_found")
    store.event("INFO", f"Aggiornamento del nodo {node_id} richiesto da {user}", "updater")
    return {"queued": queued}


@admin_routes.get("/history")
async def update_history() -> List[Dict[str, Any]]:
    events = [e for e in list(store.events) if e.get("component") == "updater"]
    return events[-HISTORY_LIMIT:][::-1]
