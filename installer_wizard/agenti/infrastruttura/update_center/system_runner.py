from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

from config import DEMO, STATE_DIR

from . import system_plan

RUN_FILE = STATE_DIR / "system_update_run.json"
PENDING_FILE = STATE_DIR / "system_update_pending.json"
APT_CONF_DIR = Path("/etc/apt/apt.conf.d")
REBOOT_FLAG = Path("/var/run/reboot-required")
CONFIRM_TTL = 600
LOCK_TIMEOUT = 300
TAIL = 1800
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_APT_ENV = ("env", "DEBIAN_FRONTEND=noninteractive", "NEEDRESTART_MODE=l", "APT_LISTCHANGES_FRONTEND=none", "LC_ALL=C")
_APT_OPTS = ("-o", f"DPkg::Lock::Timeout={LOCK_TIMEOUT}", "-o", "Dpkg::Options::=--force-confdef", "-o", "Dpkg::Options::=--force-confold")

Runner = Callable[..., Awaitable[tuple]]
_active: Optional[asyncio.Task] = None
_auto_state: Dict[str, Any] = {"enabled": None}


def _atomic_write(path: Path, data: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(data)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _read(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _tail(text: str) -> str:
    return _CONTROL.sub("", text)[-TAIL:]


def isolate(cmd: List[str]) -> List[str]:
    if shutil.which("systemd-run") and os.geteuid() == 0:
        return ["systemd-run", "--scope", "--quiet", "--collect", "--description=nuxiva-system-update", *cmd]
    return cmd


def apt_command(*args: str) -> List[str]:
    return isolate([*_APT_ENV, "apt-get", *_APT_OPTS, *args])


async def simulate(sh: Runner) -> Dict[str, Any]:
    code, _ = await sh(*_APT_ENV, "apt-get", "-o", f"DPkg::Lock::Timeout={LOCK_TIMEOUT}", "update", "-qq", timeout=300)
    stale = code != 0
    _, raw = await sh(*_APT_ENV, "apt-get", "-s", "-o", "Debug::NoLocking=1", "dist-upgrade", timeout=180)
    return {"raw": raw, "stale": stale}


async def build_plan(sh: Runner, nuxiva_available: bool, nuxiva_target: str) -> Dict[str, Any]:
    sim = await simulate(sh)
    plan = system_plan.plan(sim["raw"], nuxiva_available, nuxiva_target)
    plan["stale"] = sim["stale"]
    plan["parsed"] = system_plan.parse(sim["raw"])
    return plan


def request_confirmation(plan_id: str) -> None:
    _atomic_write(PENDING_FILE, json.dumps({"plan": plan_id, "until": time.time() + CONFIRM_TTL}))


def confirmation_valid(plan_id: str) -> bool:
    data = _read(PENDING_FILE)
    return data.get("plan") == plan_id and float(data.get("until") or 0) > time.time()


def clear_confirmation() -> None:
    PENDING_FILE.unlink(missing_ok=True)


def last_run() -> Dict[str, Any]:
    return _read(RUN_FILE)


def running() -> bool:
    return _active is not None and not _active.done()


def reboot_required() -> bool:
    return REBOOT_FLAG.exists()


class _Run:
    def __init__(self, plan: Dict[str, Any], event: Callable[[str, str], None]) -> None:
        self.data: Dict[str, Any] = {
            "plan": plan["id"],
            "status": "running",
            "started": time.time(),
            "finished": None,
            "steps": [],
            "reboot_required": False,
            "risk": plan["risk"],
        }
        self.event = event
        self.save()

    def save(self) -> None:
        _atomic_write(RUN_FILE, json.dumps(self.data, ensure_ascii=False))

    def step(self, step_id: str, status: str, detail: str = "") -> None:
        self.data["steps"].append({"id": step_id, "status": status, "at": time.time(), "detail": _tail(detail)})
        self.event("ERROR" if status == "failed" else "INFO", f"Aggiornamento di sistema: {step_id} {status}")
        self.save()

    def finish(self, status: str) -> None:
        self.data["status"] = status
        self.data["finished"] = time.time()
        self.data["reboot_required"] = reboot_required()
        self.save()


async def _snapshot(sh: Runner, parsed: Dict[str, Any]) -> str:
    names = [c["name"] for c in parsed.get("upgrades", []) if system_plan.valid_package(c["name"])][:400]
    if not names:
        return ""
    _, out = await sh("dpkg-query", "-W", "-f=${Package}=${Version}\\n", *names, timeout=60)
    return out


async def _debian(sh: Runner, run: _Run, plan: Dict[str, Any]) -> bool:
    run.step("snapshot", "running")
    run.data["rollback"] = _tail(await _snapshot(sh, plan.get("parsed", {})))
    run.step("snapshot", "done")
    run.step("debian", "running")
    code, out = await sh(*apt_command("-y", "dist-upgrade"), timeout=3600)
    if code == 0:
        run.step("debian", "done")
        return True
    run.step("recovery", "running", out)
    await sh(*isolate([*_APT_ENV, "dpkg", "--configure", "-a"]), timeout=900)
    code2, out2 = await sh(*apt_command("-y", "-f", "install"), timeout=900)
    run.step("recovery", "done" if code2 == 0 else "failed", out2)
    run.step("debian", "failed", out)
    return False


async def execute(
    sh: Runner,
    plan: Dict[str, Any],
    apply_nuxiva: Callable[[], Awaitable[bool]],
    event: Callable[[str, str], None],
) -> Dict[str, Any]:
    run = _Run(plan, event)
    try:
        debian_ok = True
        if any(s["id"] == "debian" for s in plan["steps"]):
            debian_ok = await _debian(sh, run, plan)
        if any(s["id"] == "nuxiva" for s in plan["steps"]):
            if not debian_ok:
                run.step("nuxiva", "skipped", "debian_failed")
            else:
                run.step("nuxiva", "running")
                run.finish("restarting")
                applied = await apply_nuxiva()
                run.data["status"] = "done" if applied else "failed"
                run.step("nuxiva", "done" if applied else "failed")
        run.finish("done" if debian_ok and run.data["status"] != "failed" else "failed")
    except asyncio.CancelledError:
        run.step("abort", "failed", "cancelled")
        run.finish("failed")
        raise
    except Exception as exc:
        run.step("abort", "failed", str(exc))
        run.finish("failed")
    finally:
        clear_confirmation()
    return run.data


def start(
    sh: Runner,
    plan: Dict[str, Any],
    apply_nuxiva: Callable[[], Awaitable[bool]],
    event: Callable[[str, str], None],
) -> bool:
    global _active
    if running():
        return False
    _active = asyncio.get_running_loop().create_task(execute(sh, plan, apply_nuxiva, event))
    return True


async def sync_auto_security(sh: Runner, enabled: bool, event: Callable[[str, str], None]) -> str:
    if DEMO or os.environ.get("NUXIVA_TEST_AUTH") == "1" or os.geteuid() != 0 or not APT_CONF_DIR.is_dir():
        return "skipped"
    if _auto_state["enabled"] is enabled:
        return "unchanged"
    if enabled:
        code, out = await sh("dpkg-query", "-W", "-f=${Status}", "unattended-upgrades", timeout=30)
        if code != 0 or "install ok installed" not in out:
            code, out = await sh(*apt_command("-y", "install", "--no-install-recommends", "unattended-upgrades"), timeout=900)
            if code != 0:
                event("ERROR", "Aggiornamenti automatici di sicurezza: installazione di unattended-upgrades non riuscita")
                return "failed"
    changed = False
    for item in system_plan.auto_config(enabled):
        target = APT_CONF_DIR / item["name"]
        try:
            current = target.read_text(encoding="utf-8")
        except OSError:
            current = None
        if current != item["content"]:
            _atomic_write(target, item["content"], 0o644)
            changed = True
    _auto_state["enabled"] = enabled
    if changed:
        event("INFO", "Aggiornamenti automatici di sicurezza " + ("attivati" if enabled else "disattivati"))
    return "changed" if changed else "unchanged"
