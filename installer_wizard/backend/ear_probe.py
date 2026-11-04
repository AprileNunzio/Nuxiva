import re
import time
from collections.abc import Awaitable, Callable

UNIT = "nuxiva-ear"
WARMUP_S = 180
CRASH_LOOP = 3
ERROR_RE = re.compile(r"(Error|Exception|Traceback|Killed|out of memory|oom-kill|No module named|Permission denied|Address already in use)")
SAFE_RE = re.compile(r"[^\w\s.,:;()'\"/=+\-\[\]{}]")
PROPERTIES = ("ActiveState", "SubState", "NRestarts", "ExecMainStartTimestampMonotonic", "Result")

Shell = Callable[..., Awaitable[tuple[int, str]]]


def _parse(out: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in out.splitlines():
        key, sep, value = line.partition("=")
        if sep and key in PROPERTIES:
            values[key] = value.strip()
    return values


def _int(value: str | None) -> int:
    try:
        return int(value or 0)
    except ValueError:
        return 0


def _uptime(started_us: int) -> float | None:
    if started_us <= 0:
        return None
    return max(0.0, time.monotonic() - started_us / 1_000_000)


async def last_error(sh: Shell) -> str:
    code, out = await sh("journalctl", "-u", UNIT, "-n", "80", "--no-pager", "-o", "cat", timeout=5)
    if code != 0:
        return ""
    for line in reversed(out.splitlines()):
        if ERROR_RE.search(line):
            return SAFE_RE.sub("", line.split("] ", 1)[-1]).strip()[:160]
    return ""


async def diagnose(sh: Shell) -> dict:
    code, out = await sh("systemctl", "show", UNIT, "--property=" + ",".join(PROPERTIES), timeout=5)
    if code != 0:
        return {"status": "down", "detail": "Servizio di ascolto non installato"}
    state = _parse(out)
    active, sub = state.get("ActiveState", ""), state.get("SubState", "")
    restarts = _int(state.get("NRestarts"))
    uptime = _uptime(_int(state.get("ExecMainStartTimestampMonotonic")))
    crashing = restarts >= CRASH_LOOP or sub == "auto-restart"
    warming = active in ("activating", "reloading") or (active == "active" and uptime is not None and uptime < WARMUP_S)
    if warming and not crashing:
        return {"status": "warn", "starting": True,
                "detail": "In avvio: caricamento dei modelli di ascolto"}
    error = await last_error(sh)
    reason = f": {error}" if error else ""
    if crashing:
        return {"status": "down", "crashloop": True,
                "detail": f"Il servizio si riavvia di continuo ({restarts} riavvii){reason}"}
    if active in ("inactive", "failed"):
        return {"status": "down", "stopped": True, "detail": f"Servizio fermo{reason}"}
    return {"status": "down", "detail": f"Servizio attivo ma la porta di ascolto non risponde{reason}"}


async def recover(sh: Shell, converge: Callable[[], Awaitable[object]], comp: dict, count: int) -> None:
    if comp.get("crashloop") or count > 2:
        await sh("systemctl", "reset-failed", UNIT, timeout=15)
        await converge()
        return
    await sh("systemctl", "restart", UNIT, timeout=60)
