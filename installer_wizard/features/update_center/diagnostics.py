from __future__ import annotations

import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Optional

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
MIN_FREE_RAM_MB = 256
WARN_FREE_RAM_MB = 512
MIN_FREE_DISK_GB = 1.0
WARN_FREE_DISK_GB = 3.0

Shell = Callable[..., Awaitable[tuple]]


@dataclass(frozen=True)
class CheckResult:
    id: str
    status: str
    metric: str
    detail: str

    def as_dict(self) -> Dict[str, str]:
        return asdict(self)


def _grade(value: float, fail_below: float, warn_below: float) -> str:
    if value < fail_below:
        return FAIL
    return WARN if value < warn_below else PASS


def check_memory() -> CheckResult:
    import psutil

    vm = psutil.virtual_memory()
    free_mb = vm.available // (1024 * 1024)
    return CheckResult("memory", _grade(free_mb, MIN_FREE_RAM_MB, WARN_FREE_RAM_MB), f"{free_mb} MB", f"{vm.percent}%")


def check_disk(root: Path) -> CheckResult:
    usage = shutil.disk_usage(str(root))
    free_gb = round(usage.free / 1024**3, 1)
    return CheckResult("disk", _grade(free_gb, MIN_FREE_DISK_GB, WARN_FREE_DISK_GB), f"{free_gb} GB", str(root))


def check_cpu() -> CheckResult:
    import psutil

    load = psutil.cpu_percent(interval=0.2)
    return CheckResult("cpu", WARN if load >= 85 else PASS, f"{load}%", f"{psutil.cpu_count(logical=True)}")


async def check_worktree(git: Shell) -> CheckResult:
    code, out = await git("status", "--porcelain", "--untracked-files=no")
    if code != 0:
        return CheckResult("worktree", FAIL, "git", out[:160])
    changed = [line for line in out.splitlines() if line.strip()]
    return CheckResult("worktree", WARN if changed else PASS, str(len(changed)), "\n".join(changed[:5]))


async def check_ci(rev: str, ci_status: Callable[[str], Awaitable[str]]) -> CheckResult:
    if not rev:
        return CheckResult("ci", FAIL, "", "no_revision")
    status = await ci_status(rev)
    grade = {"success": PASS, "pending": WARN, "untested": WARN, "unknown": WARN}.get(status, FAIL)
    return CheckResult("ci", grade, rev[:7], status)


async def check_service(sh: Shell, unit: str) -> CheckResult:
    code, out = await sh("systemctl", "is-active", unit, timeout=10)
    state = (out or "").strip().splitlines()[-1] if out else "unknown"
    return CheckResult("service", PASS if code == 0 and state == "active" else FAIL, state, unit)


def check_last_good(current: str, last_good: Optional[str]) -> CheckResult:
    if not last_good:
        return CheckResult("rollback_point", WARN, "", "missing")
    return CheckResult("rollback_point", PASS, last_good[:7], "current" if last_good == current else "previous")


def check_mesh_engine() -> CheckResult:
    from server.features.mesh_coordinator.p2p_mesh import p2p_mesh

    native = p2p_mesh.crdt is not None
    key = "collaudo.probe"
    stamp = str(int(time.time()))
    p2p_mesh.set_crdt_setting(key, stamp)
    readback = str(p2p_mesh.get_crdt_setting(key))
    return CheckResult("mesh_engine", PASS if readback == stamp else FAIL, "rust" if native else "python", readback)


async def run_all(steps: List[Callable[[], Awaitable[CheckResult]]]) -> Dict[str, object]:
    results: List[CheckResult] = []
    for step in steps:
        try:
            results.append(await step())
        except Exception as exc:
            results.append(CheckResult(getattr(step, "check_id", "unknown"), FAIL, type(exc).__name__, str(exc)[:200]))
    return {
        "timestamp": time.time(),
        "all_passed": all(r.status != FAIL for r in results),
        "tests": [r.as_dict() for r in results],
    }
