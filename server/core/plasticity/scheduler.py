import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable

from server.core.plasticity.service import PlasticityService

logger = logging.getLogger("nuxiva.plasticity.rem")

REM_HOUR = 3
REM_MINUTE = 30


def seconds_until_rem(now: datetime) -> float:
    target = now.replace(hour=REM_HOUR, minute=REM_MINUTE, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


async def rem_loop(service: Callable[[], PlasticityService]) -> None:
    while True:
        await asyncio.sleep(seconds_until_rem(datetime.now()))
        try:
            outcome = await asyncio.to_thread(service().consolidate)
        except Exception:
            logger.exception("REM consolidation crashed")
            continue
        if outcome.is_ok:
            logger.info("REM consolidation: %d decayed, %d pruned, %d kept", len(outcome.value["decayed"]),
                        len(outcome.value["pruned"]), outcome.value["kept"])
        else:
            logger.error("REM consolidation failed (%s)", outcome.error.code)
