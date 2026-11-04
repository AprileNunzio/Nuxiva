from __future__ import annotations

import asyncio
import logging
from typing import Any

import updater
from features.auto_update.self_healing import self_healer
from state import store

log = logging.getLogger("nuxiva.auto_update")


class AutoUpdateService:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    async def execute_boot_healing_and_update(self) -> dict[str, Any]:
        async with self._lock:
            heal_results = self_healer.run_all()
            update_applied = False
            try:
                update_applied = await updater.priority_update("boot_autonomous")
            except Exception as exc:
                log.error("Errore non fatale durante l'aggiornamento all'avvio: %s", exc)
            return {
                "healed": heal_results,
                "update_applied": update_applied,
                "local_rev": await updater.current_rev(),
            }

    async def check_updates(self, fresh: bool = True) -> dict[str, Any]:
        try:
            return await updater.check(fetch_timeout=45, fresh=fresh)
        except Exception as exc:
            log.warning("Controllo aggiornamenti online fallito: %s", exc)
            return {
                "available": False,
                "check_error": str(exc),
                "local_rev": await updater.current_rev(),
            }

    async def trigger_update(self, force: bool = False) -> dict[str, Any]:
        async with self._lock:
            try:
                success = await updater.apply(reason="autonomous_trigger", fetch_timeout=60, force=force)
                return {
                    "success": success,
                    "local_rev": await updater.current_rev(),
                    "state": store.update,
                }
            except Exception as exc:
                log.error("Errore durante l'applicazione dell'aggiornamento: %s", exc)
                return {
                    "success": False,
                    "error": str(exc),
                    "local_rev": await updater.current_rev(),
                }


update_service = AutoUpdateService()
