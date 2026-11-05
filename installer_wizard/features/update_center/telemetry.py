from __future__ import annotations

import asyncio
import platform
import time
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple

from features.update_center import guard, native
from features.update_center.progress import UpdateProgress

Shell = Callable[..., Awaitable[Tuple[int, str]]]

UNITS = ("nuxiva-supervisor", "nuxiva-core", "nuxiva-agency", "nuxiva-voice", "nuxiva-vision", "nuxiva-ear",
         "nuxiva-netguard", "nuxiva-sandbox")
SERVICES_TTL = 10.0
STATES = {"active", "inactive", "failed", "activating", "deactivating", "reloading", "unknown"}

_services: Dict[str, Any] = {"at": 0.0, "items": []}
_pending: Dict[str, Any] = {"key": None, "signature": None, "impact": None}


async def services(sh: Shell) -> list:
    if time.time() - _services["at"] < SERVICES_TTL:
        return _services["items"]
    _, out = await sh("systemctl", "is-active", *UNITS, timeout=5)
    lines = out.splitlines()
    items = []
    for index, unit in enumerate(UNITS):
        state = lines[index].strip() if index < len(lines) else "unknown"
        items.append({"unit": unit, "state": state if state in STATES else "unknown"})
    _services.update(at=time.time(), items=items)
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
                branch: str) -> Dict[str, Any]:
    target = info.get("target_rev") or (info.get("remote_rev") if info.get("available") else None)
    analysis, units = await asyncio.gather(pending_analysis(git, info.get("local_rev"), target), services(sh))
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
