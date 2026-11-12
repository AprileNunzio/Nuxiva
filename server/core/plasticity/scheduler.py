import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Optional, Sequence

from server.core.core_platform.result import Result
from server.core.plasticity.service import PlasticityService

logger = logging.getLogger("nuxiva.plasticity.rem")

REM_HOUR = 3
REM_MINUTE = 30
CATCH_UP_AFTER_SECONDS = 36 * 3600.0
CATCH_UP_DELAY_SECONDS = 300.0

NightTask = tuple[str, Callable[[], Awaitable[Result]]]

_last: dict[str, Any] = {}


def last_night() -> dict[str, Any]:
    return dict(_last)


def seconds_until_rem(now: datetime) -> float:
    target = now.replace(hour=REM_HOUR, minute=REM_MINUTE, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def overdue(last_run: Optional[float], now: float) -> bool:
    return last_run is not None and (now - last_run) > CATCH_UP_AFTER_SECONDS


def _summary(outcome: Result) -> dict[str, Any]:
    return {"ok": True, **outcome.value} if outcome.is_ok and isinstance(outcome.value, dict) else (
        {"ok": True} if outcome.is_ok else {"ok": False, "error": outcome.error.code})


async def run_night(service: Callable[[], PlasticityService], tasks: Sequence[NightTask] = ()) -> dict[str, Any]:
    report: dict[str, Any] = {"at": time.time()}
    try:
        consolidated = await asyncio.to_thread(service().consolidate)
        report["consolidation"] = _summary(consolidated)
    except Exception:
        logger.exception("REM consolidation crashed")
        report["consolidation"] = {"ok": False, "error": "crashed"}
    for name, task in tasks:
        try:
            report[name] = _summary(await task())
        except Exception:
            logger.exception("Night task %s crashed", name)
            report[name] = {"ok": False, "error": "crashed"}
    _last.clear()
    _last.update(report)
    logger.info("Night cycle finished: %s", {key: value.get("ok") for key, value in report.items() if isinstance(value, dict)})
    return report


async def rem_loop(service: Callable[[], PlasticityService], tasks: Sequence[NightTask] = ()) -> None:
    previous = await asyncio.to_thread(service().last_run)
    if previous.is_ok and overdue(previous.value, time.time()):
        await asyncio.sleep(CATCH_UP_DELAY_SECONDS)
        await run_night(service, tasks)
    while True:
        await asyncio.sleep(seconds_until_rem(datetime.now()))
        await run_night(service, tasks)
