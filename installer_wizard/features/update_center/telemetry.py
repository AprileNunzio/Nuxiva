from __future__ import annotations

import asyncio
import platform
import time
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple

from features.update_center import guard, native
from features.update_center.progress import UpdateProgress

Shell = Callable[..., Awaitable[Tuple[int, str]]]

UNITS = ("nuxiva-supervisor", "nuxiva-core", "nuxiva-agency", "nuxiva-display", "nuxiva-voice", "nuxiva-vision",
         "nuxiva-ear", "nuxiva-netguard", "nuxiva-sandbox")
CORE_UNIT = "nuxiva-core"
CORE_CONTAINER = "nuxiva-core"
SERVICES_TTL = 10.0
STATES = {"active", "inactive", "failed", "activating", "deactivating", "reloading", "unknown"}
CONTAINER_STATES = {"running": "active", "restarting": "activating", "created": "activating", "removing": "deactivating",
                    "paused": "inactive", "exited": "inactive", "dead": "failed"}
HEALTH_STATES = {"healthy": "active", "starting": "activating", "unhealthy": "failed"}
INSPECT_FORMAT = "{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}"

_services: Dict[str, Any] = {"at": 0.0, "runtime": None, "items": []}
_pending: Dict[str, Any] = {"key": None, "signature": None, "impact": None}


def container_state(code: int, out: str) -> str:
    if code != 0:
        return "inactive"
    parts = out.split()
    status = parts[0] if parts else ""
    if status == "running" and len(parts) > 1:
        return HEALTH_STATES.get(parts[1], "unknown")
    return CONTAINER_STATES.get(status, "unknown")


async def services(sh: Shell, runtime: str = "native") -> list:
    if time.time() - _services["at"] < SERVICES_TTL and _services["runtime"] == runtime:
        return _services["items"]
    _, out = await sh("systemctl", "is-active", *UNITS, timeout=5)
    lines = out.splitlines()
    items = []
    for index, unit in enumerate(UNITS):
        state = lines[index].strip() if index < len(lines) else "unknown"
        items.append({"unit": unit, "state": state if state in STATES else "unknown"})
    if runtime == "docker":
        code, raw = await sh("docker", "inspect", "--format", INSPECT_FORMAT, CORE_CONTAINER, timeout=5)
        state = container_state(code, raw)
        items = [{"unit": CORE_UNIT, "state": state} if item["unit"] == CORE_UNIT else item for item in items]
    _services.update(at=time.time(), runtime=runtime, items=items)
    return items


async def pending_analysis(git: guard.Git, local: Optional[str], target: Optional[str]) -> Dict[str, Any]:
    if not local or not target or local == target or not native.valid_rev(local) or not native.valid_rev(target):
        return {"signature": None, "impact": None}
    key = f"{local}:{target}"
    if _pending["key"] != key:
        signature, impact = await asyncio.gather(guard.signature(git, target), guard.impact(git, local, target))
        _pending.update(key=key, signature=signature, impact=impact)
    return {"signature": _pending["signature"], "impact": _pending["impact"]}


async def build(git: guard.Git, sh: Shell, info: Dict[str, Any], tracker: UpdateProgress, root: Path,
                branch: str, runtime: str = "native") -> Dict[str, Any]:
    target = info.get("target_rev") or (info.get("remote_rev") if info.get("available") else None)
    analysis, units = await asyncio.gather(pending_analysis(git, info.get("local_rev"), target), services(sh, runtime))
    _, git_version = await git("--version", timeout=5)
    view = tracker.view()
    return {
        "engine": {"name": native.ENGINE, "version": native.ENGINE_VERSION},
        "host": {"python": platform.python_version(), "git": git_version.removeprefix("git version ").strip()[:32],
                 "branch": branch[:64], "root": root.name},
        "run": view["run"],
        "console": view["console"],
        "changelog": native.changelog("\n".join(info.get("changelog") or [])),
        "pending": analysis,
        "services": units,
        "stages": [stage for stage, _ in native.STAGES],
    }
