import asyncio
import logging
import os
import time

import health
import packages
import sysinfo
import updater
from config import VERSION

DEMO: bool = False
from state import store
from steps import STEP_BY_ID, STEPS, converge_step, run_pipeline

log = logging.getLogger("nuxiva.supervisor")

ERROR_RETRY_SECONDS = 120
ERROR_RETRY_MAX = 30 * 60
NATIVE_RELOAD_SECONDS = 20.0
NATIVE_RELOAD_PHASES = frozenset({"READY", "DEGRADED", "ERROR"})


class Orchestrator:
    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.busy = False
        self.installer: asyncio.Task | None = None

    async def boot(self) -> None:
        store.boot_count += 1
        store.save()
        from features.brain.configuration import migrate_legacy
        migrate_legacy()
        from node_api import enforce_local_ollama_off
        await asyncio.to_thread(enforce_local_ollama_off)
        try:
            packages.migrate()
        except (OSError, ValueError):
            log.exception("Pacchetti installati non confermati")
        await self._reconcile_brain()
        from features.auto_update.self_healing import self_healer
        self_healer.run_all()
        pending = updater.pending()
        if pending:
            base_phase, label = "UPDATING", "Verifica della nuova versione…"
        elif not store.installed:
            base_phase, label = "INSTALLING", "Preparazione dell'installazione…"
        else:
            base_phase, label = "BOOTING", "Verifica e attivazione dei sistemi…"
        store.event("INFO", f"Avvio supervisore v{VERSION} (boot #{store.boot_count})", "supervisor")
        import setup_api
        if await setup_api.apply_answers_file():
            store.event("INFO", "Configurazione applicata dal file di risposte", "setup")
        elif not setup_api.done():
            log.warning("Codice per la prima configurazione da un altro dispositivo: %s", setup_api.guard.code)

        from features.auto_update.boot_updater import boot_updater
        boot_res = await boot_updater.execute_boot_check()
        if boot_res.get("applied"):
            return
        failures = 0
        while True:
            store.set_phase(base_phase, label)
            store.retry_at = 0
            async with self.lock:
                self.busy = True
                try:
                    ok = await run_pipeline()
                except Exception as exc:
                    log.exception("Errore inatteso nella pipeline")
                    store.last_error = f"Errore interno del supervisore: {exc}"
                    store.event("ERROR", store.last_error, "supervisor")
                    ok = False
                finally:
                    self.busy = False
            if ok:
                store.pipeline_failed = False
                break
            store.pipeline_failed = True
            if await updater.priority_update("correttivo dopo un errore"):
                return
            if pending and await updater.finish_pending(False):
                return
            wait = min(ERROR_RETRY_MAX, ERROR_RETRY_SECONDS * 2 ** min(failures, 4))
            failures += 1
            store.retry_at = time.time() + wait
            store.set_phase("ERROR", f"Nuovo tentativo automatico tra {wait // 60} minuti "
                                     f"(tentativo {failures}); verifico anche se esistono correzioni su GitHub")
            await asyncio.sleep(wait)

        degraded = any(rec.get("status") == "failed" for rec in store.steps.values())
        if degraded and await updater.priority_update("correttivo per un componente non riuscito"):
            return
        if not store.installed:
            store.installed = True
            store.installed_at = time.time()
            store.event("INFO", "Installazione completata", "supervisor")
        if pending:
            await updater.finish_pending(True)
        else:
            await updater.mark_good()
        store.save()
        health.publish(await health.probe_all())
        store.progress = 100
        store.set_phase("READY", "Tutti i sistemi operativi")
        self.installer = asyncio.create_task(self.install_background())

    @staticmethod
    async def _reconcile_brain() -> None:
        import brain_intent
        from fastapi import HTTPException
        from settings import apply_config
        try:
            updates = brain_intent.reconcile()
            if updates:
                await apply_config(updates, "riconciliazione: chiave API del cervello cloud già configurata")
        except (OSError, ValueError, HTTPException):
            log.exception("Scelta del cervello non verificata")

    async def _quiet_step(self, step_id: str) -> bool:
        return await converge_step(STEP_BY_ID[step_id], quiet=True)

    async def install_background(self) -> None:
        from background import queue
        await queue.run(self.lock)

    async def ensure(self, step_ids: list[str], reason: str = "") -> bool:
        ok = True
        async with self.lock:
            for step_id in step_ids:
                if step_id in STEP_BY_ID:
                    store.event("INFO", f"Installo ora «{STEP_BY_ID[step_id].title}»{': ' + reason if reason else ''}", step_id)
                    ok = await self._quiet_step(step_id) and ok
        return ok

    async def converge(self, only: list[str] | None = None, reason: str = "", force: bool = False) -> bool:
        if self.lock.locked():
            return False
        async with self.lock:
            self.busy = True
            previous = store.phase
            if previous in ("READY", "DEGRADED"):
                store.set_phase("DEGRADED", reason or "Manutenzione in corso")
            try:
                ok = await run_pipeline(only=only, force=force)
            finally:
                self.busy = False
            health.publish(await health.probe_all())
            if previous in ("READY", "DEGRADED", "ERROR"):
                store.set_phase("READY" if ok else "DEGRADED",
                                "Tutti i sistemi operativi" if ok else "Intervento non riuscito: nuovo tentativo a breve")
            return ok


orch = Orchestrator()


async def converge_steps(steps: list, reason: str) -> None:
    order = [s.id for s in STEPS]
    await orch.converge(sorted({x for x in steps if x in order}, key=order.index), reason=reason)


async def telemetry_loop() -> None:
    while True:
        try:
            store.system = sysinfo.collect()
            store.touch()
        except Exception as exc:
            log.warning("Telemetria non disponibile: %s", exc)
        await asyncio.sleep(2)


async def native_reload_check() -> bool:
    import native_module
    if orch.lock.locked() or store.phase not in NATIVE_RELOAD_PHASES or not native_module.reload_needed():
        return False
    if not os.environ.get("INVOCATION_ID") or not native_module.claim_reload():
        return False
    store.event("INFO", "Nuovo motore nativo installato: riavvio il supervisore per caricarlo", "native")
    code, out = await health.sh("systemctl", "restart", "--no-block", "nuxiva-supervisor.service", timeout=15)
    if code != 0:
        log.error("Riavvio del supervisore per il nuovo motore nativo non riuscito: %s", out[-300:])
        store.event("ERROR", "Riavvio automatico per il nuovo motore nativo non riuscito", "native")
        return False
    return True


async def native_reload_loop() -> None:
    import native_module
    await asyncio.to_thread(native_module.module)
    while True:
        await asyncio.sleep(NATIVE_RELOAD_SECONDS)
        try:
            await native_reload_check()
        except OSError:
            log.exception("Controllo del motore nativo in memoria non riuscito")
