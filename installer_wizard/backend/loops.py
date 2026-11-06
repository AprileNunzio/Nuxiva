import asyncio
import json
import logging
import time

import native_core
from config import env_get
from state import store

log = logging.getLogger("nuxiva.loops")
STABLE_AFTER = 120.0
CHECK_EVERY = 10.0
BACKOFF_MIN = 1.0
REPORT_EVERY = 10
STATES = {"starting": "in avvio", "running": "in esecuzione", "restarting": "in riavvio", "done": "concluso",
          "halted": "fermo (riavvio automatico disattivato)"}


def enabled() -> bool:
    return env_get("NUXIVA_LOOPS_RESTART", "1") != "0"


def backoff_max() -> float:
    try:
        return max(5.0, min(600.0, float(env_get("NUXIVA_LOOPS_BACKOFF_MAX", "60"))))
    except ValueError:
        return 60.0


def stale_factor() -> float:
    try:
        return max(2.0, min(20.0, float(env_get("NUXIVA_LOOPS_STALE_FACTOR", "5"))))
    except ValueError:
        return 5.0


class Loop:

    def __init__(self, name: str, factory, period: float) -> None:
        self.name = name
        self.factory = factory
        self.period = period
        self.inner: asyncio.Task | None = None
        self.state = "in avvio"
        self.restarts = 0
        self.stalls = 0
        self.last_error = ""
        self.started = 0.0
        self.beat = time.time()

    def view(self) -> dict:
        return {"name": self.name, "state": self.state, "restarts": self.restarts, "stalls": self.stalls,
                "last_error": self.last_error, "up_s": int(time.time() - self.started) if self.started else 0,
                "heartbeat_s": int(time.time() - self.beat) if self.period else None, "period_s": self.period or None}


class Supervisor:

    def __init__(self) -> None:
        self.loops: dict[str, Loop] = {}
        engine = native_core.symbol("RustLoopBook")
        if engine is None:
            native_core.python_fallback("loops")
        self.book = engine() if engine is not None else None

    def add(self, name: str, factory, period: float = 0.0) -> None:
        self.loops[name] = Loop(name, factory, period)
        if self.book is not None and not self.book.add(name, float(period or 0.0), time.time()):
            raise ValueError(f"Servizio non registrabile: {name}")

    def beat(self, name: str) -> None:
        loop = self.loops.get(name)
        if loop:
            loop.beat = time.time()
            if self.book is not None:
                self.book.beat(name, loop.beat)

    def snapshot(self) -> list[dict]:
        if self.book is None:
            return [loop.view() for loop in self.loops.values()]
        views = json.loads(self.book.snapshot(time.time()))
        for view in views:
            view["state"] = STATES.get(view["state"], view["state"])
        return views

    def totals(self) -> dict:
        if self.book is not None:
            return json.loads(self.book.totals())
        views = self.snapshot()
        return {"loops": len(views), "running": sum(1 for v in views if v["state"] == "in esecuzione"),
                "restarts": sum(v["restarts"] for v in views), "stalls": sum(v["stalls"] for v in views)}

    async def run(self) -> None:
        jobs = [asyncio.create_task(self._supervise(loop)) for loop in self.loops.values()]
        jobs.append(asyncio.create_task(self._watch()))
        try:
            await asyncio.gather(*jobs)
        finally:
            for job in jobs:
                job.cancel()

    async def _supervise(self, loop: Loop) -> None:
        if self.book is None:
            await self._py_supervise(loop)
            return
        while True:
            loop.started = loop.beat = time.time()
            loop.state = STATES["running"]
            self.book.start(loop.name, loop.started)
            loop.inner = asyncio.create_task(loop.factory())
            try:
                await asyncio.wait({loop.inner})
            except asyncio.CancelledError:
                loop.inner.cancel()
                raise
            reason = self._reason(loop)
            outcome = "done" if reason is None else "cancelled" if loop.inner.cancelled() else "failed"
            decision = self.book.exit(loop.name, outcome, reason or "", time.time(), enabled(), BACKOFF_MIN,
                                      backoff_max(), STABLE_AFTER, REPORT_EVERY)
            if decision is None:
                raise RuntimeError(f"Servizio sconosciuto al supervisore: {loop.name}")
            action, delay, report, loop.restarts = decision
            if action == "finish":
                loop.state = STATES["done"]
                log.info("Servizio «%s» concluso", loop.name)
                return
            loop.last_error = reason
            if action == "halt":
                loop.state = STATES["halted"]
                store.event("ERROR", f"Servizio «{loop.name}» fermo: {reason}", "servizi")
                return
            loop.state = STATES["restarting"]
            if report:
                store.event("WARN", f"Servizio «{loop.name}» riavviato ({reason}), tentativo {loop.restarts}", "servizi")
            log.warning("Servizio «%s» riavviato tra %.0fs: %s", loop.name, delay, reason)
            await asyncio.sleep(delay)

    async def _py_supervise(self, loop: Loop) -> None:
        delay = BACKOFF_MIN
        while True:
            loop.started = loop.beat = time.time()
            loop.state = "in esecuzione"
            loop.inner = asyncio.create_task(loop.factory())
            try:
                await asyncio.wait({loop.inner})
            except asyncio.CancelledError:
                loop.inner.cancel()
                raise
            reason = self._reason(loop)
            if reason is None:
                loop.state = "concluso"
                log.info("Servizio «%s» concluso", loop.name)
                return
            loop.last_error = reason
            loop.restarts += 1
            if not enabled():
                loop.state = "fermo (riavvio automatico disattivato)"
                store.event("ERROR", f"Servizio «{loop.name}» fermo: {reason}", "servizi")
                return
            loop.state = "in riavvio"
            if time.time() - loop.started > STABLE_AFTER:
                delay = BACKOFF_MIN
            if loop.restarts == 1 or loop.restarts % REPORT_EVERY == 0:
                store.event("WARN", f"Servizio «{loop.name}» riavviato ({reason}), tentativo {loop.restarts}", "servizi")
            log.warning("Servizio «%s» riavviato tra %.0fs: %s", loop.name, delay, reason)
            await asyncio.sleep(delay)
            delay = min(delay * 2, backoff_max())

    @staticmethod
    def _reason(loop: Loop) -> str | None:
        inner = loop.inner
        if inner.cancelled():
            return "bloccato: riavviato dal controllo"
        exc = inner.exception()
        if exc is None:
            return None
        log.error("Servizio «%s» fermato da un errore", loop.name, exc_info=exc)
        return f"{type(exc).__name__}: {exc}"[:200]

    async def _watch(self) -> None:
        while True:
            await asyncio.sleep(CHECK_EVERY)
            now = time.time()
            if self.book is not None:
                for name in self.book.stalled(now, stale_factor()):
                    loop = self.loops.get(name)
                    if loop and loop.inner and not loop.inner.done():
                        loop.stalls += 1
                        log.warning("Servizio «%s» senza segni di vita da %.0fs: lo riavvio", name, now - loop.beat)
                        loop.inner.cancel()
                continue
            for loop in self.loops.values():
                limit = loop.period * stale_factor() if loop.period else 0.0
                if limit and loop.inner and not loop.inner.done() and now - loop.beat > limit:
                    loop.stalls += 1
                    log.warning("Servizio «%s» senza segni di vita da %.0fs: lo riavvio", loop.name, now - loop.beat)
                    loop.inner.cancel()


class DefaultModeNetwork:
    def __init__(self) -> None:
        self.last_interaction = time.time()

    def record_activity(self) -> None:
        self.last_interaction = time.time()

    def idle_for(self) -> float:
        return time.time() - self.last_interaction


default_mode_network = DefaultModeNetwork()
supervisor = Supervisor()
