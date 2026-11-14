import asyncio
import logging
import os

from agenti.collaudo import emit, hub, intake, paths, taps

log = logging.getLogger("nuxiva.collaudo")
SAMPLE_EVERY = 5.0
FLUSH_EVERY = 30.0


def _sink(raw: dict) -> None:
    try:
        hub.emit(raw)
    except (ValueError, RuntimeError, OSError) as exc:
        log.debug("collaudo: evento scartato (%s)", type(exc).__name__)


def resource_fields() -> dict:
    fields: dict = {}
    try:
        load1, load5, _ = os.getloadavg()
        fields.update(load1=round(load1, 2), load5=round(load5, 2))
        with open("/proc/meminfo", encoding="ascii") as handle:
            info = {k: int(v.split()[0]) for k, v in (line.split(":", 1) for line in handle if ":" in line)}
        total, avail = info.get("MemTotal", 0), info.get("MemAvailable", 0)
        if total:
            fields.update(mem_used_pct=round(100 * (total - avail) / total, 1), swap_used_kb=info.get("SwapTotal", 0) - info.get("SwapFree", 0))
        stat = os.statvfs(str(paths.ROOT))
        if stat.f_blocks:
            fields["disk_used_pct"] = round(100 * (1 - stat.f_bavail / stat.f_blocks), 1)
    except (OSError, ValueError):
        pass
    return fields


async def sampler(stop: asyncio.Event) -> None:
    while not stop.is_set():
        fields = resource_fields()
        if fields:
            emit.emit("resource", "info", "sample", src="collaudo", **fields)
        try:
            await asyncio.wait_for(stop.wait(), SAMPLE_EVERY)
        except asyncio.TimeoutError:
            pass


async def flusher(stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), FLUSH_EVERY)
        except asyncio.TimeoutError:
            await asyncio.to_thread(hub.get().flush)


async def run() -> None:
    from nuxiva_bus import nuxiva_bus

    hub.get()
    emit.bind_local(_sink)
    transport = await intake.serve()
    handler = taps.install_log_tap()
    subscription = taps.install_bus_tap(nuxiva_bus)
    stop = asyncio.Event()
    emit.emit("system", "info", "collaudo_started", src="collaudo", native=hub.native(), mode=int(hub.get().collaudo()))
    jobs = [asyncio.create_task(taps.journal_tail(stop)), asyncio.create_task(sampler(stop)), asyncio.create_task(flusher(stop))]
    try:
        await asyncio.gather(*jobs)
    finally:
        stop.set()
        for job in jobs:
            job.cancel()
        subscription.cancel()
        logging.getLogger().removeHandler(handler)
        emit.bind_local(None)
        transport.close()
        await asyncio.to_thread(hub.get().flush)
